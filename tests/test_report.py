from gold_scanner.report import print_v02_report
from gold_scanner.sources.markets import MarketReading
from datetime import datetime, timezone


def test_report_reads_nested_fed_target_range(capsys):
    now = datetime.now(timezone.utc)
    reading = MarketReading(
        "DXY", 98.0, 98.5, 99.0, -0.5, -1.0, "index", "test", now, 50.0, "BULLISH GOLD", "test"
    )
    fed = {"target_range": {"lower": 3.50, "upper": 3.75, "date": "2026-09-07"}}
    bls = {"latest": {}, "upcoming_releases": []}
    markets = {"dxy": reading, "us10y": reading, "real_yields": reading, "xauusd": reading}

    print_v02_report(fed, bls, markets)
    output = capsys.readouterr().out
    assert "Target range: 3.50% - 3.75%" in output
    assert "Effective data date: 2026-09-07" in output
