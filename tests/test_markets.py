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
    monkeypatch.setattr(markets, "_treasury_month_history", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("timeout")))
    try:
        markets._treasury_history("real")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert str(exc) == "timeout"
