from __future__ import annotations

from datetime import datetime, timezone
import csv
import io
import re
import requests

FED_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FRED_UPPER_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARU"
FRED_LOWER_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFEDTARL"


def fetch_target_range(timeout: int = 20) -> dict:
    """Fetch the latest Fed target range from FRED.

    The underlying series source is the Board of Governors/FOMC.
    """
    values = {}
    for name, url in (("upper", FRED_UPPER_CSV), ("lower", FRED_LOWER_CSV)):
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(r.text)))
        rows = [x for x in rows if x.get("DFEDTARU") or x.get("DFEDTARL")]
        if not rows:
            raise RuntimeError(f"No FRED data returned for {name}")
        row = rows[-1]
        raw = row.get("DFEDTARU") or row.get("DFEDTARL")
        values[name] = {
            "date": row["observation_date"],
            "value": float(raw),
        }

    return {
        "lower": values["lower"]["value"],
        "upper": values["upper"]["value"],
        "date": min(values["lower"]["date"], values["upper"]["date"]),
    }


def _extract_2026_meetings(html: str) -> list[dict]:
    """Parse the official Fed FOMC calendar page conservatively."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)

    # Matches the month + day ranges used by the Fed calendar.
    pattern = re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2})(?:-(\d{1,2}))?"
    )

    meetings = []
    seen = set()
    for m in pattern.finditer(text):
        month, start, end = m.groups()
        start_i = int(start)
        end_i = int(end or start)
        # Only keep plausible 2026 FOMC date ranges.
        if not (1 <= start_i <= 31 and 1 <= end_i <= 31):
            continue
        key = (month, start_i, end_i)
        if key in seen:
            continue
        seen.add(key)
        meetings.append({
            "source": "Federal Reserve",
            "year": 2026,
            "month": month,
            "start_day": start_i,
            "end_day": end_i,
        })

    # The page contains other month/day references, so filter to the
    # eight known 2026 FOMC meetings from the official calendar structure.
    expected = {
        ("January", 27, 28),
        ("March", 17, 18),
        ("April", 28, 29),
        ("June", 16, 17),
        ("July", 28, 29),
        ("September", 15, 16),
        ("October", 27, 28),
        ("December", 8, 9),
    }
    return [x for x in meetings if (x["month"], x["start_day"], x["end_day"]) in expected]


def fetch_fomc_calendar(timeout: int = 20) -> list[dict]:
    r = requests.get(FED_CALENDAR_URL, timeout=timeout)
    r.raise_for_status()
    return _extract_2026_meetings(r.text)


def fetch_v01_snapshot() -> dict:
    return {
        "source": "Federal Reserve / FRED",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "target_range": fetch_target_range(),
        "fomc_2026": fetch_fomc_calendar(),
    }
