from gold_scanner.sources import markets


def test_pct_change():
    assert round(markets._pct_change(110, 100), 2) == 10.0


def test_score_direction():
    score = markets._signed_score(-0.3, -0.8, 0.3, 0.8, positive_is_bullish=False)
    assert score == 100.0
    assert markets._direction(score) == "BULLISH GOLD"


def test_make_reading_yield_uses_percentage_points():
    rows = [("2026-09-01", 4.00), ("2026-09-02", 4.05), ("2026-09-03", 4.10),
            ("2026-09-04", 4.15), ("2026-09-07", 4.20), ("2026-09-08", 4.25)]
    reading = markets._make_reading("US10Y", rows, "%", "U.S. Treasury", False, 0.05, 0.10)
    assert round(reading.change_1d, 3) == 0.05
    assert round(reading.change_5d, 3) == 0.25


def test_treasury_parser():
    html = '''
    <table><tr><th>Date</th><th>5 YR</th><th>10 YR</th></tr>
    <tr><td>09/03/2026</td><td>2.10</td><td>2.42</td></tr>
    <tr><td>09/04/2026</td><td>2.12</td><td>2.40</td></tr></table>
    '''
    parser = markets._TreasuryTableParser()
    parser.feed(html)
    assert [r for r in parser.rows if r[0] == "09/04/2026"][0][2] == "2.40"


def test_treasury_month_history_parses_mock(monkeypatch):
    class Response:
        text = '''
        <table><tr><th>Date</th><th>5 YR</th><th>7 YR</th><th>10 YR</th></tr>
        <tr><td>09/03/2026</td><td>2.17</td><td>2.29</td><td>2.43</td></tr>
        <tr><td>09/04/2026</td><td>2.18</td><td>2.30</td><td>2.42</td></tr></table>
        '''

    monkeypatch.setattr(markets, "_get", lambda *args, **kwargs: Response())
    rows = markets._treasury_month_history("real", 2026, 9)
    assert rows[-1] == ("2026-09-04", 2.42)


def test_xaus_history_parses_json(monkeypatch):
    class Response:
        def json(self):
            return {"points": [
                {"d": "2026-09-01", "c": 3400.0},
                {"d": "2026-09-02", "c": 3410.0},
                {"d": "2026-09-03", "c": 3420.0},
            ]}

    monkeypatch.setattr(markets, "_get", lambda *args, **kwargs: Response())
    rows = markets._xaus_history()
    assert rows[-1] == ("2026-09-03", 3420.0)


def test_xaus_history_rejects_insufficient_data(monkeypatch):
    class Response:
        def json(self):
            return {"points": [{"d": "2026-09-03", "c": 3420.0}]}

    monkeypatch.setattr(markets, "_get", lambda *args, **kwargs: Response())
    try:
        markets._xaus_history()
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "fewer than 2" in str(exc)



def test_treasury_history_uses_previous_month_when_current_succeeds_but_is_short(monkeypatch):
    calls = []
    def fake_month(kind, year, month):
        calls.append((kind, year, month))
        if len(calls) == 1:
            return [("2026-09-08", 2.41)]
        return [("2026-08-31", 2.40), ("2026-09-01", 2.41)]
    monkeypatch.setattr(markets, "_treasury_month_history", fake_month)
    rows = markets._treasury_history("real", limit=2)
    assert rows == [("2026-09-01", 2.41), ("2026-09-08", 2.41)]


def test_treasury_history_propagates_current_month_failure(monkeypatch):
    fail = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("timeout"))
    monkeypatch.setattr(markets, "_treasury_xml_month_history", fail)
    monkeypatch.setattr(markets, "_treasury_month_history", fail)
    try:
        markets._treasury_history("real")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "timeout" in str(exc)


def test_treasury_xml_month_history_parses_mock(monkeypatch):
    class Response:
        content = b"""<?xml version=\"1.0\"?><feed xmlns:b=\"urn:example\"><entry><b:recorddate>2026-09-04</b:recorddate><b:bc_10year>2.43</b:bc_10year></entry></feed>"""
    monkeypatch.setattr(markets, "_get", lambda *args, **kwargs: Response())
    rows = markets._treasury_xml_month_history("real", 2026, 9)
    assert rows == [("2026-09-04", 2.43)]


def test_unavailable_reading_is_neutral():
    reading = markets._unavailable_reading("10Y Real Yield", "%", "timeout")
    assert reading.source == "UNAVAILABLE"
    assert reading.score == 0.0
    assert reading.direction == "NEUTRAL"
    assert reading.change_1d is None


def test_market_snapshot_does_not_abort_when_real_yield_sources_fail(monkeypatch):
    def fail_real(kind, *args, **kwargs):
        if kind == "real":
            raise RuntimeError("timeout")
        return [("2026-09-08", 4.78), ("2026-09-07", 4.77)]
    monkeypatch.setattr(markets, "_treasury_history", fail_real)
    monkeypatch.setattr(markets, "_fred_history", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fred unavailable")))
    monkeypatch.setattr(markets, "_yahoo_history", lambda symbol, *args, **kwargs: [("2026-09-07", 98.9), ("2026-09-08", 98.8)] if symbol == "DX-Y.NYB" else [("2026-09-07", 4440), ("2026-09-08", 4450)])
    monkeypatch.setattr(markets, "_xaus_history", lambda: [("2026-09-07", 4440), ("2026-09-08", 4450)])
    snapshot = markets.fetch_market_snapshot()
    assert snapshot["real_yields"].source == "UNAVAILABLE"
    assert snapshot["dxy"].source != "UNAVAILABLE"
    assert snapshot["xauusd"].source != "UNAVAILABLE"


def test_treasury_history_uses_latest_available_prior_business_day(monkeypatch):
    def fake_month(kind, year, month):
        if (year, month) == (2026, 9):
            return [("2026-09-04", 2.43)]
        return []
    monkeypatch.setattr(markets, "_treasury_xml_month_history", fake_month)
    monkeypatch.setattr(markets, "_treasury_month_history", fake_month)
    rows = markets._treasury_history("real", limit=2)
    assert rows[-1] == ("2026-09-04", 2.43)


def test_report_marks_previous_observation(capsys):
    from gold_scanner.report import print_v02_report
    from datetime import datetime, timezone
    old = datetime(2026, 9, 4, tzinfo=timezone.utc)
    reading = markets.MarketReading("10Y Real Yield", 2.43, 2.42, 2.40, 0.01, 0.03, "%", "U.S. Treasury", old, -35.6, "BEARISH GOLD", "test")
    same = markets.MarketReading("DXY", 98, 99, 100, -1, -2, "index", "test", old, 79.3, "BULLISH GOLD", "test")
    fed = {"target_range": {"lower": 3.5, "upper": 3.75, "date": "2026-09-04"}}
    bls = {"latest": {}, "upcoming_releases": []}
    print_v02_report(fed, bls, {"dxy": same, "us10y": same, "real_yields": reading, "xauusd": same})
    output = capsys.readouterr().out
    assert "dato anterior (2026-09-04)" in output

def test_trading_economics_real_yield_current_parses_public_page(monkeypatch):
    class Response:
        text = '<div>Actual</div><div>2.43</div><div>US 10Y TIPS</div>'
    monkeypatch.setattr(markets, "_get", lambda *args, **kwargs: Response())
    rows = markets._trading_economics_real_yield_current()
    assert rows[-1][1] == 2.43


def test_market_snapshot_uses_trading_economics_before_fred(monkeypatch):
    def fail_treasury(kind, *args, **kwargs):
        raise RuntimeError("treasury unavailable")
    monkeypatch.setattr(markets, "_treasury_history", fail_treasury)
    monkeypatch.setattr(markets, "_trading_economics_real_yield_current", lambda: [("2026-09-08", 2.43)])
    monkeypatch.setattr(markets, "_fred_history", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fred unavailable")))
    monkeypatch.setattr(markets, "_yahoo_history", lambda symbol, *args, **kwargs: [
        ("2026-09-07", 98.9), ("2026-09-08", 98.8)
    ] if symbol == "DX-Y.NYB" else [("2026-09-07", 4440), ("2026-09-08", 4450)])
    monkeypatch.setattr(markets, "_xaus_history", lambda: [("2026-09-07", 4440), ("2026-09-08", 4450)])
    snapshot = markets.fetch_market_snapshot()
    assert snapshot["real_yields"].value == 2.43
    assert "Trading Economics" in snapshot["real_yields"].source
