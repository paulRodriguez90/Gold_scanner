from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import io
import time
from typing import Optional

import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
STOOQ_QUOTE = "https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"

HEADERS = {"User-Agent": "GoldScanner/0.2 (+https://github.com/)"}


@dataclass
class MarketReading:
    name: str
    value: float
    previous_1d: Optional[float]
    previous_5d: Optional[float]
    change_1d: Optional[float]
    change_5d: Optional[float]
    unit: str
    source: str
    observed_at: datetime
    score: float = 0.0
    direction: str = "NEUTRAL"
    reason: str = ""


def _pct_change(current: float, previous: Optional[float]) -> Optional[float]:
    if previous is None or previous == 0:
        return None
    return (current / previous - 1.0) * 100.0


def _signed_score(one_day: Optional[float], five_day: Optional[float],
                  one_day_full_scale: float, five_day_full_scale: float,
                  positive_is_bullish: bool = True) -> float:
    vals = []
    if one_day is not None:
        vals.append(max(-1.0, min(1.0, one_day / one_day_full_scale)))
    if five_day is not None:
        vals.append(max(-1.0, min(1.0, five_day / five_day_full_scale)))
    if not vals:
        return 0.0
    raw = sum(vals) / len(vals) * 100.0
    return raw if positive_is_bullish else -raw


def _direction(score: float) -> str:
    if score >= 20:
        return "BULLISH GOLD"
    if score <= -20:
        return "BEARISH GOLD"
    return "NEUTRAL"


def _get(url: str, params: Optional[dict] = None, timeout: int = 20) -> requests.Response:
    last_exc = None
    for attempt in range(2):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == 0:
                time.sleep(0.5)
    raise last_exc  # type: ignore[misc]


def _fred_history(series: str, limit: int = 8) -> list[tuple[str, float]]:
    r = _get(FRED_CSV.format(series=series))
    rows = []
    for row in csv.DictReader(io.StringIO(r.text)):
        value = row.get(series)
        if value in (None, "", "."):
            continue
        try:
            rows.append((row["DATE"], float(value)))
        except (KeyError, ValueError):
            continue
    if not rows:
        raise RuntimeError(f"FRED returned no usable observations for {series}")
    return rows[-limit:]


def _yahoo_history(symbol: str, range_: str = "10d") -> list[tuple[str, float]]:
    r = _get(YAHOO_CHART.format(symbol=symbol), params={"range": range_, "interval": "1d", "events": "history"})
    payload = r.json()
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    closes = result["indicators"]["quote"][0].get("close", [])
    rows = []
    from datetime import datetime as _dt
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        rows.append((_dt.fromtimestamp(ts, tz=timezone.utc).date().isoformat(), float(close)))
    if not rows:
        raise RuntimeError(f"Yahoo returned no usable observations for {symbol}")
    return rows


def _stooq_quote(symbol: str) -> float:
    r = _get(STOOQ_QUOTE.format(symbol=symbol))
    rows = list(csv.DictReader(io.StringIO(r.text)))
    if not rows:
        raise RuntimeError(f"Stooq returned no quote for {symbol}")
    close = rows[0].get("Close")
    if close in (None, "", "N/D"):
        raise RuntimeError(f"Stooq returned no close for {symbol}")
    return float(close)


def _make_reading(name: str, rows: list[tuple[str, float]], unit: str, source: str,
                  bullish_when_rising: bool, one_day_scale: float, five_day_scale: float) -> MarketReading:
    current = rows[-1][1]
    p1 = rows[-2][1] if len(rows) >= 2 else None
    p5 = rows[-6][1] if len(rows) >= 6 else rows[0][1] if rows else None
    # For yields we pass absolute changes (percentage points), while price/index
    # series use percentage changes below.
    if unit == "%":
        c1 = None if p1 is None else current - p1
        c5 = None if p5 is None else current - p5
    else:
        c1 = _pct_change(current, p1)
        c5 = _pct_change(current, p5)
    score = _signed_score(c1, c5, one_day_scale, five_day_scale, bullish_when_rising)
    direction = _direction(score)
    reason = f"1d={c1:+.3f} | 5d={c5:+.3f}" if c1 is not None and c5 is not None else "insufficient history"
    observed = datetime.fromisoformat(rows[-1][0]).replace(tzinfo=timezone.utc)
    return MarketReading(name, current, p1, p5, c1, c5, unit, source, observed, score, direction, reason)


def fetch_market_snapshot() -> dict[str, MarketReading]:
    """Fetch DXY, US10Y, 10Y real yield and XAUUSD.

    DXY/XAUUSD use Yahoo Finance with a Stooq quote fallback for gold.
    US10Y and real yields use official FRED series DGS10 and DFII10.
    """
    out: dict[str, MarketReading] = {}

    dxy_rows = _yahoo_history("DX-Y.NYB")
    out["dxy"] = _make_reading("DXY", dxy_rows, "index", "Yahoo Finance / ICE", False, 0.30, 0.80)

    us10y_rows = _fred_history("DGS10")
    out["us10y"] = _make_reading("US10Y", us10y_rows, "%", "FRED / U.S. Treasury", False, 0.05, 0.10)

    real_rows = _fred_history("DFII10")
    out["real_yields"] = _make_reading("10Y Real Yield", real_rows, "%", "FRED / U.S. Treasury", False, 0.04, 0.08)

    try:
        xau_rows = _yahoo_history("XAUUSD=X")
        xau_source = "Yahoo Finance"
    except Exception:
        # Stooq is a fallback for the spot gold symbol. If its historical API
        # changes, the scanner still reports the upstream error rather than
        # silently inventing a value.
        xau_close = _stooq_quote("xauusd")
        today = datetime.now(timezone.utc).date().isoformat()
        xau_rows = [(today, xau_close)]
        xau_source = "Stooq"
    out["xauusd"] = _make_reading("XAUUSD", xau_rows, "price", xau_source, True, 0.60, 1.50)

    return out
