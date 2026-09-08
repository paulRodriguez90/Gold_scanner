from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Optional

import requests

TE_API = "https://api.tradingeconomics.com"
TE_PUBLIC = {
    "cpi": "https://tradingeconomics.com/united-states/consumer-price-index-cpi",
    "core_cpi": "https://tradingeconomics.com/united-states/core-inflation-rate",
    "ppi": "https://tradingeconomics.com/united-states/producer-price-inflation-mom",
    "nfp": "https://tradingeconomics.com/united-states/non-farm-payrolls",
    "unemployment": "https://tradingeconomics.com/united-states/unemployment-rate",
}

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
    if not s or s in {"-", "N/A", "NA", "null"}:
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
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "GoldScanner/0.5"})
    r.raise_for_status()
    return r.json()


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


def _public_page_event(key: str, url: str) -> Optional[EconomicEvent]:
    """Best-effort public-page fallback. Never fabricates consensus."""
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 GoldScanner/0.5"})
    r.raise_for_status()
    text = re.sub(r"\s+", " ", r.text)
    # Public TE pages commonly expose the current row as Actual / Previous / Consensus.
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


def fetch_consensus_events(start: str, end: str) -> list[EconomicEvent]:
    """Fetch actual/previous/consensus for the macro releases used by Gold Scanner.

    Trading Economics is preferred because it publishes survey consensus and
    official actual values. An API key is optional; when absent we use the
    public indicator pages as a best-effort fallback. Missing consensus is
    represented as None, never as a guessed value.
    """
    indicators = {
        "cpi": "Consumer Price Index CPI",
        "core_cpi": "Core Inflation Rate",
        "ppi": "Producer Price Inflation MoM",
        "nfp": "Non Farm Payrolls",
        "unemployment": "Unemployment Rate",
    }
    out: list[EconomicEvent] = []
    for key, indicator in indicators.items():
        try:
            items = _api_events(indicator, start, end)
            out.extend(_event_from_te(x, key) for x in items)
            if items:
                continue
        except Exception:
            pass
        try:
            event = _public_page_event(key, TE_PUBLIC[key])
            if event:
                out.append(event)
        except Exception:
            pass
    # newest event per key/date first
    out.sort(key=lambda x: (x.date, x.key), reverse=True)
    return out
