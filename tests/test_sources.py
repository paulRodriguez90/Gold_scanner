from gold_scanner.sources.bls import _parse_ics_date, _fallback_release_calendar
from gold_scanner.sources.fed import _extract_2026_meetings


def test_ics_date():
    value = _parse_ics_date("DTSTART:20260911T123000Z")
    assert value.year == 2026
    assert value.month == 9
    assert value.day == 11


def test_fomc_parser():
    html = """
    <html><body>
    2026 FOMC Meetings
    September 15-16
    October 27-28
    December 8-9
    </body></html>
    """
    meetings = _extract_2026_meetings(html)
    assert ("September", 15, 16) in {
        (m["month"], m["start_day"], m["end_day"]) for m in meetings
    }


def test_bls_fallback_contains_key_releases():
    calendar = _fallback_release_calendar()
    titles = [event["title"] for event in calendar]
    assert any("Consumer Price Index for August 2026" in title for title in titles)
    assert any("Producer Price Index for August 2026" in title for title in titles)
    assert any("Employment Situation for September 2026" in title for title in titles)


def test_bls_single_series_uses_path(monkeypatch):
    from gold_scanner.sources import bls

    seen = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "status": "REQUEST_SUCCEEDED",
                "Results": {
                    "series": [{
                        "seriesID": "CUUR0000SA0",
                        "data": [{
                            "year": "2026",
                            "period": "M08",
                            "periodName": "August",
                            "value": "325.000",
                        }],
                    }]
                },
            }

    def fake_get(url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr(bls.requests, "get", fake_get)
    result = bls.fetch_latest_series("CUUR0000SA0")

    assert seen["url"].endswith("/CUUR0000SA0")
    assert "params" not in seen["kwargs"]
    assert result["value"] == 325.0


def test_market_reading_score_direction():
    from datetime import datetime, timezone
    from gold_scanner.sources.markets import MarketReading

    r = MarketReading("DXY", 100, 99, 98, 1.01, 2.04, "index", "test", datetime.now(timezone.utc), -80, "BEARISH GOLD", "test")
    assert r.score < 0
    assert r.direction == "BEARISH GOLD"


def test_fed_snapshot_target_range_contract(monkeypatch):
    from gold_scanner.sources import fed

    monkeypatch.setattr(fed, "fetch_target_range", lambda: {
        "lower": 3.50, "upper": 3.75, "date": "2026-09-07"
    })
    monkeypatch.setattr(fed, "fetch_fomc_calendar", lambda: [])
    snapshot = fed.fetch_v01_snapshot()
    assert snapshot["target_range"]["lower"] == 3.50
    assert snapshot["target_range"]["upper"] == 3.75
    assert snapshot["target_range"]["date"] == "2026-09-07"

def test_bls_history_series_ids_and_parsing(monkeypatch):
    from gold_scanner.sources import bls
    assert bls.SERIES["cpi_core"] == "CUUR0000SA0L1E"
    assert bls.SERIES["ppi_core"] == "WPSFD49104"


def test_macro_scoring_weaker_employment_is_bullish():
    from gold_scanner.macro_scoring import calculate_macro_impact
    hist = lambda vals: [{"date": d, "value": v} for d,v in vals]
    snap={
        "cpi_core": hist([("2026-07", 333), ("2026-06", 334), ("2025-07", 330)]),
        "ppi_core": hist([("2026-07", 156), ("2026-06", 157), ("2025-07", 155)]),
        "nonfarm_payrolls": hist([("2026-08", 159075), ("2026-07", 159300)]),
        "unemployment_rate": hist([("2026-08", 4.1), ("2026-07", 4.0)]),
        "target_range": {"lower":3.5,"upper":3.75,"date":"2026-09-08"},
        "target_history": [{"date":"2026-09-08","lower":3.5,"upper":3.75},{"date":"2026-07-29","lower":3.5,"upper":3.75}],
    }
    result=calculate_macro_impact(snap)
    assert result.factors[1].score > 0


def test_surprise_scoring_uses_consensus_without_guessing():
    from gold_scanner.macro_scoring import calculate_surprise_impact
    from gold_scanner.sources.calendar import EconomicEvent
    events = [
        EconomicEvent("cpi", "2026-08-12", 2.40, 2.50, 2.60, "%", "test", 3, True),
        EconomicEvent("nfp", "2026-09-04", 162000, 159000, 150000, "persons", "test", 3, True),
    ]
    result = calculate_surprise_impact({}, events)
    assert result["events"]
    assert result["score"] > 0


def test_surprise_scoring_skips_missing_consensus():
    from gold_scanner.macro_scoring import calculate_surprise_impact
    from gold_scanner.sources.calendar import EconomicEvent
    events = [EconomicEvent("cpi", "2026-08-12", 2.40, 2.50, None, "%", "test", 3, True)]
    result = calculate_surprise_impact({}, events)
    assert result["events"] == []
    assert result["score"] == 0.0


def test_surprise_scoring_reports_missing_consensus_explicitly():
    from gold_scanner.macro_scoring import calculate_surprise_impact
    from gold_scanner.sources.calendar import EconomicEvent
    events = [EconomicEvent("cpi", "2026-08-12", 2.40, 2.50, None, "%", "test", 3, True)]
    result = calculate_surprise_impact({}, events)
    assert "CPI" in result["missing_consensus"]
    assert "Sin consenso" in result["explanation"]


def test_surprise_supports_core_ppi():
    from gold_scanner.macro_scoring import calculate_surprise_impact
    from gold_scanner.sources.calendar import EconomicEvent
    events = [EconomicEvent("core_ppi", "2026-08-14", 0.20, 0.10, 0.30, "%", "test", 3, True)]
    result = calculate_surprise_impact({}, events)
    assert result["events"][0]["label"] == "Core PPI"
    assert result["score"] > 0
