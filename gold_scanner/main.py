from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .sources.markets import fetch_market_snapshot
from .market_scoring import market_factor_scores
from .report import print_v02_report
from .scoring import weighted_score, classify


def run():
    fed = fetch_fed()
    bls = fetch_bls()
    markets = fetch_market_snapshot()

    print_v02_report(fed, bls, markets)

    factor_scores = market_factor_scores(markets)
    score = weighted_score(factor_scores)
    print("\nMARKET FACTOR SCORES")
    for name, value in factor_scores.items():
        print(f"{name}: {value:+.1f}")
    print(f"\nCURRENT GOLD SCORE: {score:.1f}")
    print(f"STATE: {classify(score)}")
    print("V0.2 STATUS: MARKET DRIVERS CONNECTED; MACRO/NEWS ENGINE STILL IN PROGRESS.")


if __name__ == "__main__":
    run()
