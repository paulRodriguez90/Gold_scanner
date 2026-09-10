from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from datetime import datetime, timezone


def clamp(x: float, lo=-100.0, hi=100.0) -> float:
    return max(lo, min(hi, float(x)))

@dataclass(frozen=True)
class MacroFactor:
    name: str
    score: float
    direction: str
    reason: str
    data_date: str | None = None

@dataclass(frozen=True)
class MacroImpact:
    score: float
    state: str
    factors: tuple[MacroFactor, ...]
    explanation: str
    missing: tuple[str, ...]
    next_fomc: str | None = None


def _direction(score: float) -> str:
    if score >= 20: return "BULLISH GOLD"
    if score <= -20: return "BEARISH GOLD"
    return "NEUTRAL"


def _trend_score(delta: float | None, scale: float, positive_bullish: bool) -> float:
    if delta is None: return 0.0
    raw = clamp(delta / scale) * 100.0
    return raw if positive_bullish else -raw


def _obs(history: list[dict[str, Any]], n: int) -> dict[str, Any] | None:
    return history[n] if n < len(history) else None


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0): return None
    return (a / b - 1.0) * 100.0


def _inflation_factor(snapshot: dict) -> MacroFactor:
    cpi = snapshot.get("cpi_core") or snapshot.get("cpi_all_items")
    ppi = snapshot.get("ppi_core") or snapshot.get("ppi_final_demand")
    signals = []
    dates = []
    details = []
    for label, hist in (("CPI", cpi), ("PPI", ppi)):
        if not hist: continue
        cur = _obs(hist, 0); prev = _obs(hist, 1); year = _obs(hist, 12)
        if not cur: continue
        mom = _pct(cur["value"], prev["value"] if prev else None)
        yoy = _pct(cur["value"], year["value"] if year else None)
        # Rising inflation is bearish for gold; falling inflation is bullish.
        s1 = _trend_score(mom, 0.30, False)
        s2 = _trend_score(yoy, 3.0, False)
        s = (s1 + s2) / 2 if (mom is not None and yoy is not None) else (s1 if mom is not None else s2)
        signals.append(s); dates.append(cur.get("date")); details.append(f"{label} MoM={mom:+.2f}% YoY={yoy:+.2f}%" if mom is not None and yoy is not None else label)
    if not signals:
        return MacroFactor("inflation", 0, "NEUTRAL", "Sin datos de inflación suficientes")
    score = clamp(sum(signals) / len(signals))
    return MacroFactor("inflation", score, _direction(score), "; ".join(details), max(dates) if dates else None)


def _employment_factor(snapshot: dict) -> MacroFactor:
    nfp = snapshot.get("nonfarm_payrolls") or []
    unemp = snapshot.get("unemployment_rate") or []
    scores = []; details=[]; dates=[]
    if nfp:
        cur=_obs(nfp,0); prev=_obs(nfp,1)
        if cur and prev:
            change = cur["value"] - prev["value"]
            # Weaker payroll growth is bullish gold. +/- 150k maps to +/-100.
            s = _trend_score(change, 150.0, False)
            scores.append(s); dates.append(cur.get("date")); details.append(f"NFP cambio={change:+.0f}k")
    if unemp:
        cur=_obs(unemp,0); prev=_obs(unemp,1)
        if cur and prev:
            delta = cur["value"] - prev["value"]
            # Rising unemployment is bullish gold.
            s = _trend_score(delta, 0.30, True)
            scores.append(s); dates.append(cur.get("date")); details.append(f"desempleo cambio={delta:+.2f} pp")
    if not scores:
        return MacroFactor("employment",0,"NEUTRAL","Sin datos de empleo suficientes")
    score=clamp(sum(scores)/len(scores))
    return MacroFactor("employment",score,_direction(score),"; ".join(details),max(dates) if dates else None)


def _fed_factor(snapshot: dict) -> MacroFactor:
    target=snapshot.get("target_range") or {}
    history=snapshot.get("target_history") or []
    if not target.get("lower") or not target.get("upper"):
        return MacroFactor("fed",0,"NEUTRAL","Sin rango objetivo de la Fed")
    current=(target["lower"]+target["upper"])/2
    prior=None
    if len(history)>1:
        prior=(history[1]["lower"]+history[1]["upper"])/2
    if prior is None:
        return MacroFactor("fed",0,"NEUTRAL","Rango Fed disponible; sin cambio previo verificable",target.get("date"))
    change=current-prior
    # Lower policy rate is bullish gold; higher is bearish.
    score=clamp(-change/0.50*100)
    reason=f"cambio del punto medio={change:+.2f} pp"
    return MacroFactor("fed",score,_direction(score),reason,target.get("date"))


def calculate_macro_impact(snapshot: dict) -> MacroImpact:
    factors=[]; missing=[]
    for fn,name in ((_inflation_factor,"inflation"),(_employment_factor,"employment"),(_fed_factor,"fed")):
        f=fn(snapshot); factors.append(f)
        if f.reason.startswith("Sin datos"):
            missing.append(name)
    weights={"inflation":0.40,"employment":0.30,"fed":0.30}
    score=clamp(sum(f.score*weights[f.name] for f in factors))

    if score>=60: state="COMPRA FUERTE"
    elif score>=30: state="COMPRA MODERADA"
    elif score>=10: state="ALCISTA"
    elif score>-10: state="INDECISION"
    elif score>-30: state="BAJISTA"
    elif score>-60: state="VENTA MODERADA"
    else: state="VENTA FUERTE"

    directional = 1 if score > 0 else -1 if score < 0 else 0
    if directional and missing:
        state = f"{'ALCISTA' if directional > 0 else 'BAJISTA'} — ESPERAR CONFIRMACIÓN MACRO ({', '.join(missing)})"
    elif directional and 10 <= abs(score) < 30:
        # At this layer there is no price input, so the missing confirmation
        # is necessarily fundamental rather than price-based.
        state = f"{'ALCISTA' if directional > 0 else 'BAJISTA'} — ESPERAR CONFIRMACIÓN MACRO"
    elif directional and 30 <= abs(score) < 60:
        # Moderate fundamental pressure without enough strength for a strong
        # state is better described as moderate, not as an unexplained wait.
        state = "COMPRA MODERADA" if directional > 0 else "VENTA MODERADA"

    if missing and state in {"COMPRA FUERTE","COMPRA MODERADA"}:
        state=f"{'ALCISTA' if directional > 0 else 'BAJISTA'} — ESPERAR CONFIRMACIÓN MACRO ({', '.join(missing)})"
    explanation="; ".join(f"{f.name} {f.score:+.1f}" for f in factors)
    if missing: explanation += ". Datos faltantes: " + ", ".join(missing)
    return MacroImpact(round(score,1),state,tuple(factors),explanation,tuple(missing),snapshot.get("next_fomc"))


def _latest_event(events, key: str):
    rows = [e for e in (events or []) if getattr(e, "key", None) == key and getattr(e, "released", False)]
    return max(rows, key=lambda e: e.date) if rows else None


def _surprise_score(actual, consensus, scale, positive_bullish=True):
    if actual is None or consensus is None:
        return None
    surprise = actual - consensus
    raw = clamp(surprise / scale) * 100.0
    return raw if positive_bullish else -raw


def _latest_event(events, keys):
    if isinstance(keys, str):
        keys = (keys,)
    rows = [e for e in (events or []) if getattr(e, "key", None) in keys and getattr(e, "released", False)]
    return max(rows, key=lambda e: (e.date, e.release_time or "")) if rows else None


def _surprise_score(actual, consensus, scale, positive_bullish=True):
    if actual is None or consensus is None:
        return None
    surprise = actual - consensus
    raw = clamp(surprise / scale) * 100.0
    return raw if positive_bullish else -raw


def _event_surprise_score(event, scale, positive_bullish):
    """Score a released event without letting index-level CPI values explode.

    Some public calendars expose CPI as an index level (for example 333.92 vs
    334.85) while others expose the inflation rate. The generic CPI scale is
    appropriate for percentage releases but is far too small for index levels
    and can produce nonsense such as +465. For index-level values, use a
    0.5%% relative surprise scale, then keep the final score bounded to [-100,+100].
    """
    if event.actual is None or event.consensus is None:
        return None
    if event.key in {"cpi", "core_cpi"} and (event.metric or "value") == "value" and event.consensus != 0:
        relative_surprise = (event.actual - event.consensus) / abs(event.consensus)
        raw = clamp((relative_surprise / 0.005) * 100.0)
        return raw if positive_bullish else -raw
    return _surprise_score(event.actual, event.consensus, scale, positive_bullish)


SURPRISE_WEIGHTS = {"cpi": .20, "core_cpi": .20, "ppi": .15, "core_ppi": .10, "nfp": .20, "unemployment": .15}


def _surprise_specs():
    return [
        (("cpi",), "CPI", 0.20, False),
        (("core_cpi",), "Core CPI", 0.15, False),
        (("ppi",), "PPI", 0.30, False),
        (("core_ppi",), "Core PPI", 0.25, False),
        (("nfp",), "NFP", 150_000.0, False),
        (("unemployment",), "Unemployment", 0.15, True),
    ]


def calculate_surprise_impact(snapshot: dict, events=None, state=None) -> dict:
    """Return active macro surprise memory plus upcoming consensus.

    Released actual-vs-consensus events are stored outside this function by
    ``macro_state``. Their latest valid score remains active until a newer
    release replaces it. Future events never become surprise scores merely
    because they have a forecast.
    """
    events = events or []
    state = state or {"surprises": {}}
    specs = _surprise_specs()
    labels = {k[0]: label for k, label, _, _ in specs}
    scales = {k[0]: (scale, bullish) for k, _, scale, bullish in specs}
    released_rows = []
    upcoming_rows = []
    missing_consensus = []

    today = datetime.now(timezone.utc).date().isoformat()
    for e in events:
        if e.key not in labels:
            continue
        label = labels[e.key]
        # Calendar providers can expose summary/last-known values alongside
        # a future event. A future-dated event is never a released Actual,
        # regardless of what the provider placed in its Actual field.
        is_future = bool(e.date and e.date > today)
        scale, positive_bullish = scales[e.key]
        metric_label = f"{label} {e.metric.upper()}" if e.metric and e.metric != "value" else label
        if is_future or e.actual is None:
            if e.consensus is not None:
                upcoming_rows.append({"key": e.key, "metric": e.metric, "label": metric_label, "consensus": e.consensus, "previous": e.previous, "date": e.date, "source": e.source, "release_time": e.release_time})
            continue
        if e.consensus is None:
            missing_consensus.append(label)
            continue
        score = _event_surprise_score(e, scale, positive_bullish)
        released_rows.append({
            "key": e.key, "metric": e.metric, "label": metric_label, "actual": e.actual,
            "consensus": e.consensus, "previous": e.previous,
            "surprise": e.actual - e.consensus, "score": round(score, 1),
            "date": e.date, "source": e.source, "release_time": e.release_time,
        })

    # State is the source of truth for the currently active surprise. If the
    # current calendar contains a newer released event, it supersedes the old
    # stored event for that same metric after main() updates the state.
    # Merge persisted surprises with freshly fetched releases. Fresh data wins
    # for the same key/metric/date, which also migrates stale scores produced by
    # older scanner versions.
    active_by_release = {}
    for row in (state.get('surprises') or {}).values():
        if row.get('actual') is not None and row.get('consensus') is not None:
            ident = (row.get('key'), row.get('metric') or 'value', row.get('date') or '')
            active_by_release[ident] = dict(row)
    for row in released_rows:
        ident = (row.get('key'), row.get('metric') or 'value', row.get('date') or '')
        active_by_release[ident] = row
    active = list(active_by_release.values())

    # Only the latest release per indicator/metric contributes to the active
    # score. This means a monthly indicator does not accumulate old surprises.
    latest = {}
    for row in active:
        identity = (row.get('key'), row.get('metric') or 'value')
        current = latest.get(identity)
        if current is None or (row.get('date') or '', row.get('release_time') or '') > (current.get('date') or '', current.get('release_time') or ''):
            latest[identity] = row
    rows = list(latest.values())
    rows.sort(key=lambda r: (r.get('date') or '', r.get('key') or '', r.get('metric') or ''))
    upcoming_rows.sort(key=lambda r: (r["date"], r["key"], r.get("metric") or ""))

    # Public calendars often return duplicate representations of the same
    # indicator: one row with Actual/Consensus and another summary row with
    # Actual but no consensus. Do not report "sin consenso verificable" when
    # a valid consensus already exists for the active release/key.
    active_keys_with_consensus = {
        (r.get('key'), r.get('metric') or 'value')
        for r in rows
        if r.get('consensus') is not None
    }
    missing_consensus = [
        label for label in sorted(set(missing_consensus))
        if not any(labels.get(k) == label for k, _metric in active_keys_with_consensus)
    ]

    if not rows:
        msg = "No hay una sorpresa publicada vigente con consenso. Los datos macro publicados siguen formando parte del Macro Fundamental."
        if missing_consensus:
            msg += " Sin consenso verificable: " + ", ".join(sorted(set(missing_consensus))) + "."
        return {"score": 0.0, "state": "SIN SORPRESA VIGENTE", "events": [], "upcoming": upcoming_rows, "missing_consensus": sorted(set(missing_consensus)), "explanation": msg}

    total_w = sum(SURPRISE_WEIGHTS.get(r.get("key"), 0.0) for r in rows)
    score = clamp(sum(float(r.get("score", 0.0)) * SURPRISE_WEIGHTS.get(r.get("key"), 0.0) for r in rows) / total_w) if total_w else 0.0
    if score >= 30: state_name = "FAVORABLE AL ORO"
    elif score <= -30: state_name = "DESFAVORABLE AL ORO"
    else: state_name = "MIXTO / LEVE"
    explanation = "; ".join(f'{r["label"]} {r["score"]:+.1f} (vigente)' for r in rows)
    if missing_consensus:
        explanation += "; sin consenso verificable: " + ", ".join(sorted(set(missing_consensus)))
    return {"score": round(score, 1), "state": state_name, "events": rows, "upcoming": upcoming_rows, "missing_consensus": sorted(set(missing_consensus)), "explanation": explanation}
