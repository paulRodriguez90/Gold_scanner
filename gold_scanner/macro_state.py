from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_VERSION = 1
DEFAULT_PATH = Path('.gold_scanner_state.json')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identity(row: dict[str, Any]) -> str:
    return '|'.join(str(row.get(k) or '') for k in ('key', 'metric', 'date'))


def load_state(path: str | Path = DEFAULT_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {'version': STATE_VERSION, 'updated_at': None, 'macro_context': {}, 'surprises': {}}
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            raise ValueError('invalid state')
        data.setdefault('version', STATE_VERSION)
        data.setdefault('updated_at', None)
        data.setdefault('macro_context', {})
        data.setdefault('surprises', {})
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return {'version': STATE_VERSION, 'updated_at': None, 'macro_context': {}, 'surprises': {}}


def save_state(state: dict[str, Any], path: str | Path = DEFAULT_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    state = dict(state)
    state['version'] = STATE_VERSION
    state['updated_at'] = _now()
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')
    tmp.replace(p)


def update_macro_context(state: dict[str, Any], macro_input: dict[str, Any]) -> dict[str, Any]:
    """Persist the latest published macro observations as context.

    The newest observation remains the active value until the upstream source
    publishes a newer observation. We do not replace a value with None.
    """
    context = state.setdefault('macro_context', {})
    for key, history in macro_input.items():
        if not isinstance(history, list) or not history:
            continue
        latest = history[0]
        if not isinstance(latest, dict) or latest.get('value') is None:
            continue
        previous = context.get(key) if isinstance(context.get(key), dict) else {}
        old_history = previous.get('history') if isinstance(previous.get('history'), list) else []
        merged = []
        seen = set()
        for row in list(history) + old_history:
            if not isinstance(row, dict) or row.get('value') is None:
                continue
            ident = (row.get('date'), row.get('period'), row.get('value'))
            if ident in seen:
                continue
            seen.add(ident)
            merged.append(dict(row))
        merged.sort(key=lambda r: (r.get('date') or '', r.get('period') or ''), reverse=True)
        context[key] = {
            'value': latest.get('value'),
            'date': latest.get('date'),
            'period_name': latest.get('period_name'),
            'history': merged[:24],
            'updated_at': _now(),
        }
    return state


def update_released_surprises(state: dict[str, Any], surprise_result: dict[str, Any]) -> dict[str, Any]:
    """Persist every valid released actual-vs-consensus result.

    A stored surprise stays active on future runs until a newer release for the
    same metric is observed. This is the persistent macro memory used by the
    combined score.
    """
    surprises = state.setdefault('surprises', {})
    today = datetime.now(timezone.utc).date().isoformat()
    # Remove any future-dated surprise that may have been stored by an older
    # buggy run. It can never be an active surprise before its release date.
    for ident, stored in list(surprises.items()):
        if isinstance(stored, dict) and stored.get('date') and stored.get('date') > today:
            del surprises[ident]
    for row in surprise_result.get('events', []) or []:
        if row.get('actual') is None or row.get('consensus') is None:
            continue
        if row.get('date') and row.get('date') > today:
            continue
        ident = _identity(row)
        # A new release for the same indicator/metric supersedes the older
        # release. Keep only the current active observation in persistent state.
        prefix = f"{row.get('key') or ''}|{row.get('metric') or ''}|"
        for old_ident in list(surprises):
            if old_ident.startswith(prefix) and old_ident != ident:
                del surprises[old_ident]
        previous = surprises.get(ident, {})
        surprises[ident] = {
            **previous,
            **row,
            'stored_at': _now(),
        }
    return state


def active_surprises(state: dict[str, Any]) -> list[dict[str, Any]]:
    today = datetime.now(timezone.utc).date().isoformat()
    rows = [
        r for r in (state.get('surprises') or {}).values()
        if isinstance(r, dict) and (not r.get('date') or r.get('date') <= today)
    ]
    rows.sort(key=lambda r: (r.get('date') or '', r.get('release_time') or ''), reverse=True)
    return rows


def active_surprise_score(state: dict[str, Any], weights: dict[str, float]) -> float:
    rows = active_surprises(state)
    if not rows:
        return 0.0
    total_w = sum(weights.get(r.get('key'), 0.0) for r in rows)
    if total_w <= 0:
        return 0.0
    return max(-100.0, min(100.0, sum(float(r.get('score', 0.0)) * weights.get(r.get('key'), 0.0) for r in rows) / total_w))
