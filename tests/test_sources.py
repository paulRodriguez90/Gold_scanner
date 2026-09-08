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
