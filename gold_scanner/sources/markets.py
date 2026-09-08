from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import csv
import io
import time
from html.parser import HTMLParser
import math
import xml.etree.ElementTree as ET
from typing import Optional

import requests

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
XAUS_HISTORY = "https://xaus.com/api/v1/history"
TREASURY_TEXT = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView"
TREASURY_XML = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
TRADING_ECONOMICS_TIPS = "https://tradingeconomics.com/united-states/10-year-tips-yield"

TREASURY_XML_STATIC = {
    "nominal": "https://home.treasury.gov/sites/default/files/interest-rates/yield.xml",
    "real": "https://home.treasury.gov/sites/default/files/interest-rates/real_yield.xml",
}

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


def _get(url: str, params: Optional[dict] = None, timeout: int = 10) -> requests.Response:
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


class _TreasuryTableParser(HTMLParser):
    """Small stdlib-only parser for Treasury's HTML rate tables."""

    def __init__(self) -> None:
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cells: list[str] = []
        self.current: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "tr":
            self.in_row = True
            self.cells = []
        elif self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.current = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("td", "th") and self.in_cell:
            self.cells.append(" ".join("".join(self.current).split()))
            self.current = []
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            if self.cells:
                self.rows.append(self.cells)
            self.in_row = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current.append(data)


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _treasury_xml_month_history(kind: str, year: int, month: int) -> list[tuple[str, float]]:
    """Fetch Treasury daily rates through its official XML developer feed."""
    if kind not in ("nominal", "real"):
        raise ValueError(f"Unsupported Treasury table kind: {kind}")
    data_key = "daily_treasury_yield_curve" if kind == "nominal" else "daily_treasury_real_yield_curve"
    column = "10 yr" if kind == "nominal" else "10 yr"
    urls = [
        (TREASURY_XML, {"data": data_key, "field_tdr_date_value_month": f"{year:04d}{month:02d}"}),
        (TREASURY_XML_STATIC[kind], None),
    ]
    last_exc = None
    for url, params in urls:
        try:
            r = _get(url, params=params)
            root = ET.fromstring(r.content)
            rows = []
            for entry in root.iter():
                if _xml_local_name(entry.tag) != "entry":
                    continue
                fields = {}
                for child in entry.iter():
                    name = _xml_local_name(child.tag)
                    text = (child.text or "").strip()
                    if text and name not in fields:
                        fields[name] = text
                date_text = fields.get("b:recorddate") or fields.get("recorddate") or fields.get("d:recorddate")
                value_text = fields.get("b:bc_10year") or fields.get("bc_10year") or fields.get("d:bc_10year")
                if not date_text or not value_text:
                    # Treasury XML commonly uses fields like bc_10year / bc_10year_1.
                    for k, v in fields.items():
                        lk = k.lower().replace("_", "")
                        if date_text is None and "recorddate" in lk:
                            date_text = v
                        if value_text is None and "10year" in lk and "30year" not in lk:
                            value_text = v
                if not date_text or not value_text or value_text.upper() == "N/A":
                    continue
                try:
                    dt = datetime.fromisoformat(date_text.replace("Z", "+00:00")).date()
                    value = float(value_text)
                except (ValueError, TypeError):
                    try:
                        dt = datetime.strptime(date_text, "%Y-%m-%d").date()
                        value = float(value_text)
                    except (ValueError, TypeError):
                        continue
                if dt.year == year and dt.month == month:
                    rows.append((dt.isoformat(), value))
            if rows:
                return sorted(set(rows), key=lambda x: x[0])
        except (requests.RequestException, ET.ParseError, RuntimeError) as exc:
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Treasury XML returned no {kind} observations for {year}-{month:02d}")


def _treasury_month_history(kind: str, year: int, month: int) -> list[tuple[str, float]]:
    """Fetch one month from the U.S. Treasury public daily-rate table.

    kind is either 'nominal' (10Y par yield) or 'real' (10Y real yield).
    Treasury is used here instead of FRED because GitHub-hosted runners can
    receive an empty/blocked response from FRED's graph CSV endpoint.
    """
    if kind == "nominal":
        table_type = "daily_treasury_yield_curve"
        column = "10 Yr"
    elif kind == "real":
        table_type = "daily_treasury_real_yield_curve"
        column = "10 YR"
    else:
        raise ValueError(f"Unsupported Treasury table kind: {kind}")

    url = f"{TREASURY_TEXT}?field_tdr_date_value_month={year:04d}{month:02d}&type={table_type}"
    r = _get(url)
    parser = _TreasuryTableParser()
    parser.feed(r.text)

    rows: list[tuple[str, float]] = []
    header_idx: Optional[int] = None
    for row in parser.rows:
        normalized = [cell.strip() for cell in row]
        if "Date" in normalized:
            try:
                header_idx = normalized.index("Date")
            except ValueError:
                pass
            continue
        if header_idx is None or len(normalized) <= header_idx:
            continue
        # In Treasury's table, Date is first and 10-year is a later column.
        # Find the 10Y header dynamically from the row containing the header.

    headers: Optional[list[str]] = None
    for row in parser.rows:
        if "Date" in row and any(h.upper() == column.upper() for h in row):
            headers = row
            break
    if not headers:
        raise RuntimeError(f"Treasury returned no {kind} header for {year}-{month:02d}")

    date_i = headers.index("Date")
    col_i = next(i for i, h in enumerate(headers) if h.upper() == column.upper())

    for row in parser.rows:
        if len(row) <= max(date_i, col_i) or row == headers:
            continue
        date_text = row[date_i].strip()
        value_text = row[col_i].strip()
        try:
            dt = datetime.strptime(date_text, "%m/%d/%Y").date()
            value = float(value_text)
        except (ValueError, TypeError):
            continue
        rows.append((dt.isoformat(), value))
    return rows


def _treasury_history(kind: str, limit: int = 8) -> list[tuple[str, float]]:
    """Return the most recent official observations available up to today.

    Treasury publishes the daily real-yield curve later in the U.S. session.
    If today's value is not published yet, the latest prior business day is
    intentionally used (Friday on weekends/holidays). Future-dated rows are
    ignored so the scanner never uses a value from the future.
    """
    today = datetime.now(timezone.utc).date()
    errors = []
    for loader in (_treasury_xml_month_history, _treasury_month_history):
        try:
            rows: list[tuple[str, float]] = []
            cursor = today.replace(day=1)
            for _ in range(2):
                try:
                    rows.extend(loader(kind, cursor.year, cursor.month))
                except Exception as exc:
                    errors.append(exc)
                previous_day = cursor - timedelta(days=1)
                cursor = previous_day.replace(day=1)
            rows = sorted({(d, v) for d, v in rows if d <= today.isoformat()}, key=lambda x: x[0])
            if rows:
                return rows[-limit:]
        except Exception as exc:
            errors.append(exc)
    raise RuntimeError(f"Treasury unavailable for {kind}: {errors[-1] if errors else 'no data'}")

def _trading_economics_real_yield_current() -> list[tuple[str, float]]:
    """Fetch the current 10Y TIPS yield from Trading Economics public page.

    This is a non-official fallback intended to fill the intraday gap before
    Treasury publishes its daily real-yield observation. The page exposes the
    current value publicly; historical observations remain delegated to
    Treasury/FRED.
    """
    r = _get(TRADING_ECONOMICS_TIPS, timeout=12)
    text = r.text
    import re

    # Prefer the value immediately following the page's Actual label.
    patterns = [
        r"Actual(?:\s|<[^>]*>)*([+-]?\d+(?:\.\d+)?)",
        r"US 10Y TIPS(?:\s|<[^>]*>)*([+-]?\d+(?:\.\d+)?)",
    ]
    value = None
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.I | re.S)
        if m:
            try:
                candidate = float(m.group(1))
                if -10.0 < candidate < 10.0:
                    value = candidate
                    break
            except ValueError:
                pass
    if value is None:
        raise RuntimeError("Trading Economics returned no usable 10Y TIPS value")

    # The public quote is a current market observation for today's session.
    return [(datetime.now(timezone.utc).date().isoformat(), value)]


def _unavailable_reading(name: str, unit: str, reason: str) -> MarketReading:
    return MarketReading(
        name=name, value=math.nan, previous_1d=None, previous_5d=None,
        change_1d=None, change_5d=None, unit=unit, source="UNAVAILABLE",
        observed_at=datetime.now(timezone.utc), score=0.0, direction="NEUTRAL",
        reason=reason,
    )


def _fred_history(series: str, limit: int = 8) -> list[tuple[str, float]]:
    """Legacy FRED fallback kept for non-Treasury series."""
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


def _xaus_history(limit: int = 10) -> list[tuple[str, float]]:
    """Fetch daily XAU/USD spot history from XAUS.

    XAUS exposes keyless daily XAU/USD history as JSON. Each point contains
    the date (d) and close (c). We keep only valid observations and use the
    latest points for the 1d/5d market-driver calculations.
    """
    r = _get(XAUS_HISTORY)
    payload = r.json()
    points = payload.get("points", [])
    rows: list[tuple[str, float]] = []
    for point in points:
        date_text = point.get("d")
        close = point.get("c")
        if not date_text or close in (None, ""):
            continue
        try:
            rows.append((str(date_text), float(close)))
        except (TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x[0])
    if len(rows) < 2:
        raise RuntimeError("XAUS returned fewer than 2 usable XAU/USD observations")
    return rows[-limit:]


def _make_reading(name: str, rows: list[tuple[str, float]], unit: str, source: str,
                  bullish_when_rising: bool, one_day_scale: float, five_day_scale: float) -> MarketReading:
    current = rows[-1][1]
    p1 = rows[-2][1] if len(rows) >= 2 else None
    p5 = rows[-6][1] if len(rows) >= 6 else rows[0][1] if rows else None
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
    """Fetch market drivers. A failed provider never aborts the full scanner."""
    out: dict[str, MarketReading] = {}

    try:
        dxy_rows = _yahoo_history("DX-Y.NYB")
        out["dxy"] = _make_reading("DXY", dxy_rows, "index", "Yahoo Finance / ICE", False, 0.30, 0.80)
    except Exception as exc:
        out["dxy"] = _unavailable_reading("DXY", "index", str(exc))

    try:
        us10y_rows = _treasury_history("nominal")
        us10y_source = "U.S. Treasury"
    except Exception:
        try:
            us10y_rows = _yahoo_history("^TNX")
            us10y_source = "Yahoo Finance / ^TNX fallback"
        except Exception as exc:
            out["us10y"] = _unavailable_reading("US10Y", "%", str(exc))
        else:
            out["us10y"] = _make_reading("US10Y", us10y_rows, "%", us10y_source, False, 0.05, 0.10)
    else:
        out["us10y"] = _make_reading("US10Y", us10y_rows, "%", us10y_source, False, 0.05, 0.10)

    try:
        real_rows = _treasury_history("real")
        real_source = "U.S. Treasury"
        out["real_yields"] = _make_reading("10Y Real Yield", real_rows, "%", real_source, False, 0.04, 0.08)
    except Exception as treasury_exc:
        try:
            te_rows = _trading_economics_real_yield_current()
            # Add prior official observations when available so 1d/5d changes
            # remain meaningful even when the intraday value comes from TE.
            history_rows: list[tuple[str, float]] = []
            try:
                history_rows = _treasury_history("real")
            except Exception:
                try:
                    history_rows = _fred_history("DFII10")
                except Exception:
                    history_rows = []
            combined = sorted({*history_rows, *te_rows}, key=lambda x: x[0])
            out["real_yields"] = _make_reading(
                "10Y Real Yield", combined[-8:] if combined else te_rows, "%",
                "Trading Economics / Treasury-FRED history fallback", False, 0.04, 0.08
            )
        except Exception as te_exc:
            try:
                real_rows = _fred_history("DFII10")
                out["real_yields"] = _make_reading("10Y Real Yield", real_rows, "%", "FRED / U.S. Treasury (DFII10) fallback", False, 0.04, 0.08)
            except Exception as fred_exc:
                out["real_yields"] = _unavailable_reading("10Y Real Yield", "%", f"Treasury: {treasury_exc}; Trading Economics: {te_exc}; FRED: {fred_exc}")

    try:
        xau_rows = _xaus_history()
        out["xauusd"] = _make_reading("XAUUSD", xau_rows, "price", "XAUS XAU/USD spot history", True, 0.60, 1.50)
    except Exception:
        try:
            xau_rows = _yahoo_history("GC=F")
            out["xauusd"] = _make_reading("XAUUSD (GC=F proxy)", xau_rows, "price", "Yahoo Finance / COMEX Gold futures (proxy)", True, 0.60, 1.50)
        except Exception as exc:
            out["xauusd"] = _unavailable_reading("XAUUSD", "price", str(exc))

    return out

