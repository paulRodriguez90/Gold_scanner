from datetime import datetime, timezone, timedelta

from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .sources.markets import fetch_market_snapshot
from .confluence import calculate_market_confluence
from .report import print_v03_report
from .macro_scoring import calculate_macro_impact, calculate_surprise_impact
from .sources.calendar import fetch_consensus_events
from .macro_state import load_state, save_state, update_macro_context, update_released_surprises


def _macro_input_from_state(state):
    context = state.get("macro_context") or {}
    out = {}
    for key, value in context.items():
        if not isinstance(value, dict):
            continue
        history = value.get("history")
        if isinstance(history, list) and history:
            out[key] = history
        elif value.get("value") is not None:
            out[key] = [{
                "date": value.get("date"),
                "period_name": value.get("period_name"),
                "value": value.get("value"),
            }]
    return out


def run():
    # Load state before external calls so a temporary source outage can fall
    # back to the last valid macro context and still persist the state.
    state = load_state()
    fed = {}
    bls = {}
    markets = {}
    macro_input = _macro_input_from_state(state)
    errors = []

    try:
        fed = fetch_fed()
    except Exception as exc:
        errors.append(f"Fed: {exc}")
        fed = {}

    try:
        bls = fetch_bls()
        incoming = bls.get("history", {})
        if incoming:
            macro_input.update(incoming)
    except Exception as exc:
        errors.append(f"BLS: {exc}")
        # Keep the last valid persisted BLS context. The scanner must not die
        # merely because BLS has reached its request threshold.
        bls = {
            "source": "BLS (persistent fallback)",
            "calendar": [],
            "observations": {},
            "history": macro_input,
        }

    try:
        markets = fetch_market_snapshot()
    except Exception as exc:
        errors.append(f"Markets: {exc}")
        markets = {}

    # Persist any newly retrieved macro context before calculating the report.
    state = update_macro_context(state, macro_input)

    confluence = calculate_market_confluence(markets) if markets else calculate_market_confluence({})
    fed_target = fed.get("target_range")
    fed_history = fed.get("target_history", [])
    macro_input = {
        **macro_input,
        "target_range": fed_target,
        "target_history": fed_history,
        "next_fomc": fed.get("next_fomc"),
    }
    macro = calculate_macro_impact(macro_input)

    now = datetime.now(timezone.utc)
    start = (now.date() - timedelta(days=180)).isoformat()
    end = (now.date() + timedelta(days=45)).isoformat()
    try:
        events = fetch_consensus_events(start, end)
    except Exception as exc:
        errors.append(f"Consensus calendar: {exc}")
        events = []

    surprise = calculate_surprise_impact(macro_input, events, state)
    state = update_released_surprises(state, surprise)
    save_state(state)
    surprise = calculate_surprise_impact(macro_input, events, state)

    combined_score = round(0.55 * confluence.score + 0.25 * macro.score + 0.20 * surprise["score"], 1)
    print_v03_report(fed, bls, markets, confluence, macro, combined_score, surprise, errors=errors, state=state)


if __name__ == "__main__":
    run()
