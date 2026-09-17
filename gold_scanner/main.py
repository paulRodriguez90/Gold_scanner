from datetime import datetime, timezone, timedelta

from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls, ppi_final_demand_mom
from .sources.markets import fetch_market_snapshot
from .confluence import calculate_market_confluence
from .report import print_v03_report
from .macro_scoring import calculate_macro_impact, calculate_surprise_impact
from .sources.calendar import fetch_consensus_events
from .macro_state import load_state, save_state, update_macro_context, update_released_surprises
from .bias import build_daily_bias, build_weekly_bias
from .telegram import format_telegram_message, send_telegram
from .sources.markets import fetch_technical_context


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


def _prefer_official_ppi_actual(events, bls_history):
    """Replace only PPI Final Demand MoM Actual with its official BLS value.

    Consensus/Previous remain calendar context. A secondary source can never
    overwrite an official Actual, and a previous value never becomes another
    active input.
    """
    official = ppi_final_demand_mom(bls_history)
    if not official:
        return events
    candidates = [e for e in events if e.key == "ppi" and (e.metric in {"", "mom"})]
    if not candidates:
        return events
    target = max(candidates, key=lambda e: (e.date or "", e.release_time or ""))
    from dataclasses import replace
    return [replace(e, actual=official["actual"], source=official["source"], released=True, metric="mom") if e is target else e for e in events]


def run():
    # Load state before external calls so a temporary source outage can fall
    # back to the last valid macro context and still persist the state.
    state = load_state()
    fed = {}
    bls = {}
    markets = {}
    technical = None
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

    try:
        technical = fetch_technical_context()
    except Exception as exc:
        errors.append(f"Technical XAUUSD spot 1H/5H: {exc}")

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
        events = _prefer_official_ppi_actual(events, macro_input)
    except Exception as exc:
        errors.append(f"Consensus calendar: {exc}")
        events = []

    surprise = calculate_surprise_impact(macro_input, events, state)
    state = update_released_surprises(state, surprise)
    save_state(state)
    surprise = calculate_surprise_impact(macro_input, events, state)

    # Daily context combines macro/market with grouped XAUUSD spot strength.
    # 5H describes session continuity; 1H describes recent pressure.
    technical_score = (0.60 * technical["5H"].score + 0.40 * technical["1H"].score) if technical else 0.0
    combined_score = round(
        0.45 * confluence.score + 0.25 * macro.score + 0.15 * surprise["score"]
        + 0.15 * technical_score, 1
    )

    upcoming = [e for e in (surprise.get("upcoming", []) or []) if e.get("consensus") is not None and e.get("date")]
    upcoming.sort(key=lambda row: (row.get("date", ""), row.get("release_time") or ""))
    next_event = None
    if upcoming:
        row = upcoming[0]
        next_event = f'{row.get("label", "Evento macro")} — {row.get("date")}'
    elif fed.get("next_fomc"):
        next_event = f'FOMC — {fed.get("next_fomc")}'

    weekly_bias = build_weekly_bias(macro, surprise, next_event)
    daily_bias = build_daily_bias(combined_score, confluence, macro, surprise, next_event, technical=technical)
    print_v03_report(
        fed, bls, markets, confluence, macro, combined_score, surprise,
        errors=errors, state=state, weekly_bias=weekly_bias,
        daily_bias=daily_bias, next_event=next_event, technical=technical
    )

    # Telegram is optional for local runs. In GitHub Actions, configure the
    # two repository secrets to receive the directional context automatically.
    if __import__("os").environ.get("TELEGRAM_BOT_TOKEN") and __import__("os").environ.get("TELEGRAM_CHAT_ID"):
        try:
            message = format_telegram_message(weekly_bias, daily_bias, next_event, technical=technical)
            send_telegram(message)
            print("TELEGRAM: mensaje enviado correctamente.")
        except Exception as exc:
            print(f"TELEGRAM WARNING: no se pudo enviar el mensaje: {exc}")
    else:
        print("TELEGRAM: no configurado (faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).")


if __name__ == "__main__":
    run()
