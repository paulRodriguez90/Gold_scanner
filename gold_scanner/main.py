from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .sources.markets import fetch_market_snapshot
from .confluence import calculate_market_confluence
from .report import print_v03_report
from .macro_scoring import calculate_macro_impact, calculate_surprise_impact
from .sources.calendar import fetch_consensus_events
from .macro_state import load_state, save_state, update_macro_context, update_released_surprises
from datetime import timedelta


def run():
    fed = fetch_fed()
    bls = fetch_bls()
    markets = fetch_market_snapshot()

    confluence = calculate_market_confluence(markets)
    macro_input = {**bls.get("history", {}), "target_range": fed.get("target_range"), "target_history": fed.get("target_history", []), "next_fomc": fed.get("next_fomc")}
    macro = calculate_macro_impact(macro_input)
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    # Fetch enough history to seed/recover the latest released consensus event
    # when the runner starts with an empty state. The persistent state then
    # carries that latest valid surprise across subsequent 15-minute runs.
    start = (now.date() - timedelta(days=180)).isoformat()
    end = (now.date() + timedelta(days=45)).isoformat()
    events = fetch_consensus_events(start, end)
    state = load_state()
    state = update_macro_context(state, macro_input)
    surprise = calculate_surprise_impact(macro_input, events, state)
    state = update_released_surprises(state, surprise)
    save_state(state)
    # Recalculate from persisted state so a newly released surprise becomes active immediately.
    surprise = calculate_surprise_impact(macro_input, events, state)
    combined_score = round(0.55 * confluence.score + 0.25 * macro.score + 0.20 * surprise["score"], 1)
    print_v03_report(fed, bls, markets, confluence, macro, combined_score, surprise)


if __name__ == "__main__":
    run()
