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


def test_report_reads_bls_snapshot_contract(capsys):
    now = datetime.now(timezone.utc)
    reading = MarketReading(
        "DXY", 98.0, 98.5, 99.0, -0.5, -1.0, "index", "test", now, 50.0, "BULLISH GOLD", "test"
    )
    fed = {"target_range": {"lower": 3.50, "upper": 3.75, "date": "2026-09-07"}}
    bls = {
        "observations": {
            "cpi_all_items": {"value": 325.0, "period_name": "August", "year": "2026"},
            "unemployment_rate": {"value": 4.2, "period_name": "August", "year": "2026"},
        },
        "calendar": [
            {"start": "2026-09-10T08:30:00-04:00", "title": "Producer Price Index for August 2026"}
        ],
    }
    markets = {"dxy": reading, "us10y": reading, "real_yields": reading, "xauusd": reading}

    print_v02_report(fed, bls, markets)
    output = capsys.readouterr().out
    assert "cpi_all_items: 325.0 (August 2026)" in output
    assert "unemployment_rate: 4.2 (August 2026)" in output
    assert "Producer Price Index for August 2026" in output


def test_report_filters_past_bls_releases(capsys):
    now = datetime.now(timezone.utc)
    reading = MarketReading(
        "DXY", 98.0, 98.5, 99.0, -0.5, -1.0, "index", "test", now, 50.0, "BULLISH GOLD", "test"
    )
    fed = {"target_range": {"lower": 3.50, "upper": 3.75, "date": "2026-09-07"}}
    bls = {
        "observations": {},
        "calendar": [
            {"start": "2026-01-09T08:30:00-05:00", "title": "Old release"},
            {"start": "2026-09-10T08:30:00-04:00", "title": "Producer Price Index for August 2026"},
        ],
    }
    markets = {"dxy": reading, "us10y": reading, "real_yields": reading, "xauusd": reading}
    print_v02_report(fed, bls, markets)
    output = capsys.readouterr().out
    assert "Old release" not in output
    assert "Producer Price Index for August 2026" in output


def test_report_mentions_persistent_surprise(capsys):
    # Use the existing test module fixtures/functions if available; this test only checks the source text.
    from pathlib import Path
    text = Path('gold_scanner/report.py').read_text(encoding='utf-8')
    assert 'último surprise válido permanece en la ecuación' in text
