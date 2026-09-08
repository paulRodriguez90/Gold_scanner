from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .sources.markets import fetch_market_snapshot
from .confluence import calculate_market_confluence
from .report import print_v03_report
from .macro_scoring import calculate_macro_impact


def run():
    fed = fetch_fed()
    bls = fetch_bls()
    markets = fetch_market_snapshot()

    confluence = calculate_market_confluence(markets)
    macro_input = {**bls.get("history", {}), "target_range": fed.get("target_range"), "target_history": fed.get("target_history", []), "next_fomc": fed.get("next_fomc")}
    macro = calculate_macro_impact(macro_input)
    combined_score = round(0.65 * confluence.score + 0.35 * macro.score, 1)
    print_v03_report(fed, bls, markets, confluence, macro, combined_score)


if __name__ == "__main__":
    run()
