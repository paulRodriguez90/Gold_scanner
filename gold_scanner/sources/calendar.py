from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Optional

import requests

TE_API = "https://api.tradingeconomics.com"
TE_PUBLIC = {
    "core_ppi": "https://tradingeconomics.com/united-states/ppi-ex-food-and-energy-mom",
    "cpi": "https://tradingeconomics.com/united-states/consumer-price-index-cpi",
    "core_cpi": "https://tradingeconomics.com/united-states/core-inflation-rate",
    "ppi": "https://tradingeconomics.com/united-states/producer-price-inflation-mom",
    "nfp": "https://tradingeconomics.com/united-states/non-farm-payrolls",
    "unemployment": "https://tradingeconomics.com/united-states/unemployment-rate",
}

MYFXBOOK_PUBLIC = {
    "cpi": "https://www.myfxbook.com/forex-economic-calendar/united-states/cpi",
    "core_cpi": "https://www.myfxbook.com/forex-economic-calendar/united-states/core-inflation-rate",
    "ppi": "https://www.myfxbook.com/forex-economic-calendar/united-states/ppi-mom",
    "core_ppi": "https://www.myfxbook.com/forex-economic-calendar/united-states/ppi-ex-food-energy-and-trade-mom",
    "nfp": "https://www.myfxbook.com/forex-economic-calendar/united-states/non-farm-payrolls",
    "unemployment": "https://www.myfxbook.com/forex-economic-calendar/united-states/unemployment-rate",
}

INVESTING_PUBLIC = {
    "cpi": "https://www.investing.com/economic-calendar/-1549",
    "core_cpi": "https://www.investing.com/economic-calendar/cpi-li-736",
    "ppi": "https://www.investing.com/economiccalendar/ppi-238",
    "core_ppi": "https://www.investing.com/economic-calendar/ppi-ex.-food-energy-trade-2048",
    "nfp": "https://www.investing.com/economic-calendar/nonfarm-payrolls-227",
    "unemployment": "https://www.investing.com/economic-calendar/unemployment-rate-300",
}

FOREXFACTORY_PUBLIC = "https://www.forexfactory.com/calendar"

@dataclass(frozen=True)
class EconomicEvent:
    key: str
    date: str
    actual: Optional[float]
    previous: Optional[float]
    consensus: Optional[float]
    unit: str = ""
    source: str = ""
    importance: int = 0
    released: bool = False
    release_time: Optional[str] = None


def _num(value):
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if not s or s in {"-", "—", "–", "N/A", "NA", "null"}:
        return None
    mult = 1.0
    if s.endswith("K"):
        mult = 1000.0; s = s[:-1]
    elif s.endswith("M"):
        mult = 1_000_000.0; s = s[:-1]
    elif s.endswith("B"):
        mult = 1_000_000_000.0; s = s[:-1]
    s = s.replace("%", "").strip()
    try:
        return float(s) * mult
    except ValueError:
        return None


def _get_json(url, params=None, timeout=15):
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "GoldScanner/0.5.2"})
    r.raise_for_status()
    return r.json()


def _get_html(url, timeout=15):
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 GoldScanner/0.5.2"})
    r.raise_for_status()
    return r.text


def _api_events(indicator: str, start: str, end: str) -> list[dict]:
    key = os.getenv("TRADING_ECONOMICS_API_KEY")
    if not key:
        return []
    url = f"{TE_API}/calendar/country/united%20states/indicator/{indicator}/{start}/{end}"
    data = _get_json(url, params={"c": key, "f": "json"})
    return data if isinstance(data, list) else []


def _event_from_te(item: dict, key: str) -> EconomicEvent:
    raw_date = item.get("Date") or item.get("date") or ""
    date = raw_date[:10]
    actual = item.get("ActualValue") if item.get("ActualValue") is not None else _num(item.get("Actual"))
    previous = item.get("PreviousValue") if item.get("PreviousValue") is not None else _num(item.get("Previous"))
    consensus = item.get("ForecastValue") if item.get("ForecastValue") is not None else _num(item.get("Forecast"))
    return EconomicEvent(key, date, actual, previous, consensus, item.get("Unit", ""), "Trading Economics", int(item.get("Importance") or 0), actual is not None, raw_date)


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            text = re.sub(r"\s+", " ", " ".join(self._cell)).strip()
            self._row.append(text)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _parse_date(text: str) -> str | None:
    text = text.strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    m = re.search(r"([A-Z][a-z]{2,8})\s+(\d{1,2}),\s*(\d{4})", text)
    if m:
        try:
            return datetime.strptime(m.group(0), "%B %d, %Y").date().isoformat()
        except ValueError:
            try:
                return datetime.strptime(m.group(0), "%b %d, %Y").date().isoformat()
            except ValueError:
                pass
    return None


def _parse_date_cell(text: str) -> tuple[str | None, str | None]:
    date = _parse_date(text)
    tm = re.search(r"\b(\d{1,2}:\d{2})\b", text)
    return date, tm.group(1) if tm else None


def _parse_public_calendar_rows(html: str, key: str, source: str) -> list[EconomicEvent]:
    parser = _TableParser()
    parser.feed(html)
    out: list[EconomicEvent] = []
    for row in parser.rows:
        if len(row) < 4:
            continue
        date, release_time = _parse_date_cell(row[0])
        if not date:
            # Some pages put the date in a separate first cell.
            for cell in row[:2]:
                date, release_time = _parse_date_cell(cell)
                if date:
                    break
        if not date:
            continue
        # Both Myfxbook and Investing expose Date/Time followed by
        # Previous, Consensus/Forecast, Actual. Preserve blank cells so an
        # upcoming release such as [blank, 334.85, blank] is not misread.
        cells = row[1:]
        if cells and re.fullmatch(r"\d{1,2}:\d{2}", cells[0].strip()):
            cells = cells[1:]
        if len(cells) < 3:
            continue
        previous = _num(cells[0])
        consensus = _num(cells[1])
        actual = _num(cells[2])
        if previous is None and consensus is None and actual is None:
            continue
        out.append(EconomicEvent(key, date, actual, previous, consensus, source=source, released=actual is not None, release_time=release_time))
    return out


def _public_source_events(key: str, url: str, source: str) -> list[EconomicEvent]:
    html = _get_html(url)
    return _parse_public_calendar_rows(html, key, source)


def _public_page_event(key: str, url: str) -> Optional[EconomicEvent]:
    """Legacy Trading Economics page fallback. Never fabricates consensus."""
    html = _get_html(url)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    patterns = [
        r"Actual[^0-9+-]{0,120}([+-]?\d+(?:\.\d+)?)\s+Previous[^0-9+-]{0,120}([+-]?\d+(?:\.\d+)?)\s+Consensus[^0-9+-]{0,120}([+-]?\d+(?:\.\d+)?)",
        r"Actual[^0-9+-]{0,120}([+-]?\d+(?:\.\d+)?).*?Consensus[^0-9+-]{0,120}([+-]?\d+(?:\.\d+)?)",
    ]
    for i, pat in enumerate(patterns):
        m = re.search(pat, text, re.I)
        if m:
            vals = [_num(x) for x in m.groups()]
            if i == 0:
                actual, previous, consensus = vals
            else:
                actual, consensus = vals
                previous = None
            if actual is not None or consensus is not None:
                return EconomicEvent(key, datetime.now(timezone.utc).date().isoformat(), actual, previous, consensus, source="Trading Economics public page", released=actual is not None)
    return None



def _parse_forexfactory_events(html: str) -> list[EconomicEvent]:
    """Best-effort direct Forex Factory parser for USD macro events."""
    parser = _TableParser()
    parser.feed(html)
    rows = parser.rows
    current_date = None
    mapping = {
        "cpi": ("consumer price index", "cpi"),
        "core_cpi": ("core cpi", "core consumer price index"),
        "ppi": ("ppi", "producer price index"),
        "core_ppi": ("core ppi", "ppi ex food"),
        "nfp": ("non-farm employment change", "nonfarm payrolls", "non farm payrolls"),
        "unemployment": ("unemployment rate",),
    }
    out = []
    weekdays = r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)"
    for row in rows:
        text = " | ".join(row)
        date_match = re.search(rf"{weekdays}\s+([A-Z][a-z]{{2}}\s+\d{{1,2}})", text)
        if date_match:
            month_day = date_match.group(1)
            try:
                current_date = datetime.strptime(f"{month_day} {datetime.now(timezone.utc).year}", "%b %d %Y").date().isoformat()
            except ValueError:
                pass
        if current_date is None or "USD" not in row:
            continue
        lower = text.lower()
        key = None
        for candidate, names in mapping.items():
            if any(name in lower for name in names):
                # Core must win over generic CPI/PPI.
                if candidate in {"core_cpi", "core_ppi"}:
                    key = candidate; break
                if key is None:
                    key = candidate
        if key is None:
            continue
        # Actual / Forecast / Previous are the final three value cells.
        vals = [_num(x) for x in row]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            continue
        actual = vals[-3] if len(vals) >= 3 else None
        forecast = vals[-2] if len(vals) >= 3 else vals[-1]
        previous = vals[-1] if len(vals) >= 3 else None
        # If the event is upcoming, Actual is blank; with two numeric cells
        # those are forecast and previous.
        released = actual is not None
        if len(vals) == 2:
            actual = None
            forecast, previous = vals[-2], vals[-1]
        time_match = re.search(r"\b(\d{1,2}:\d{2}(?:am|pm)?)\b", text, re.I)
        out.append(EconomicEvent(key, current_date, actual, previous, forecast, source="Forex Factory", released=released, release_time=time_match.group(1) if time_match else None))
    return out


def _forexfactory_events() -> list[EconomicEvent]:
    html = _get_html(FOREXFACTORY_PUBLIC)
    return _parse_forexfactory_events(html)

def _dedupe(events: list[EconomicEvent]) -> list[EconomicEvent]:
    seen = set()
    out = []
    for e in sorted(events, key=lambda x: (x.date, x.key, x.release_time or ""), reverse=True):
        ident = (e.key, e.date, e.actual, e.previous, e.consensus)
        if ident in seen:
            continue
        seen.add(ident)
        out.append(e)
    return out


def fetch_consensus_events(start: str, end: str) -> list[EconomicEvent]:
    """Fetch actual/previous/consensus using a resilient public-source cascade.

    Priority per indicator:
      1) Trading Economics API (when TRADING_ECONOMICS_API_KEY exists)
      2) Trading Economics public page
      3) Myfxbook public economic calendar
      4) Investing.com public economic calendar
      5) no consensus

    Sources are never averaged or combined. The first source that supplies a
    valid row wins for that indicator/date. Missing consensus stays None.
    """
    indicators = {
        "cpi": "Consumer Price Index CPI",
        "core_cpi": "Core Inflation Rate",
        "ppi": "Producer Price Inflation MoM",
        "core_ppi": "PPI Ex Food and Energy MoM",
        "nfp": "Non Farm Payrolls",
        "unemployment": "Unemployment Rate",
    }
    out: list[EconomicEvent] = []
    for key, indicator in indicators.items():
        found: list[EconomicEvent] = []
        try:
            items = _api_events(indicator, start, end)
            found.extend(_event_from_te(x, key) for x in items)
        except Exception:
            pass
        # Do not use the legacy Trading Economics page-text fallback here.
        # Its rendered page contains unrelated numeric values (including
        # dates/years and summary statistics) and does not expose a reliable
        # event date/Actual/Consensus tuple. Accepting it can manufacture
        # nonsense events such as actual=2025, consensus=2026.
        # We only trust the structured TE API or structured public calendars.
        if not found:
            try:
                found = _public_source_events(key, MYFXBOOK_PUBLIC[key], "Myfxbook")
            except Exception:
                found = []
        if not found:
            try:
                found = _public_source_events(key, INVESTING_PUBLIC[key], "Investing.com")
            except Exception:
                found = []
        if not any(e.consensus is not None for e in found):
            try:
                ff = [e for e in _forexfactory_events() if e.key == key]
                if ff:
                    found = ff
            except Exception:
                pass
        out.extend(found)
    return _dedupe(out)
