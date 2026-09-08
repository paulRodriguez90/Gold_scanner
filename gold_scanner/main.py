from .sources.fed import fetch_v01_snapshot as fetch_fed
from .sources.bls import fetch_v01_snapshot as fetch_bls
from .sources.markets import fetch_market_snapshot
from .confluence import calculate_market_confluence
from .report import print_v03_report


def run():
    fed = fetch_fed()
    bls = fetch_bls()
    markets = fetch_market_snapshot()

    confluence = calculate_market_confluence(markets)
    print_v03_report(fed, bls, markets, confluence)


if __name__ == "__main__":
    run()
