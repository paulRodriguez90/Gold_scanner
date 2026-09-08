from datetime import datetime, timezone

from gold_scanner.sources.markets import MarketReading, _make_reading


def test_rising_dxy_is_bearish_gold():
    rows = [("2026-09-01", 100.0), ("2026-09-02", 100.2), ("2026-09-03", 100.4),
            ("2026-09-04", 100.6), ("2026-09-05", 100.8), ("2026-09-06", 101.0)]
    r = _make_reading("DXY", rows, "index", "test", False, 0.30, 0.80)
    assert r.score < 0


def test_falling_real_yield_is_bullish_gold():
    rows = [("2026-09-01", 2.50), ("2026-09-02", 2.49), ("2026-09-03", 2.48),
            ("2026-09-04", 2.47), ("2026-09-05", 2.46), ("2026-09-06", 2.40)]
    r = _make_reading("10Y Real Yield", rows, "%", "test", False, 0.04, 0.08)
    assert r.score > 0
