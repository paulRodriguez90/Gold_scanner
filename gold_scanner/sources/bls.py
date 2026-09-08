from __future__ import annotations

from datetime import datetime, timezone
import requests

BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BLS_API_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"

# Official BLS series used by the scanner in V0.1.
SERIES = {
    "cpi_all_items": "CUUR0000SA0",
    "cpi_core": "CUUR0000SA0L1E",
    "ppi_final_demand": "WPSFD4",
    "ppi_core": "WPSFD49104",
    "unemployment_rate": "LNS14000000",
    "nonfarm_payrolls": "CES0000000001",
}

# The BLS ICS endpoint can return HTTP 403 from automated runners even though
# the same calendar is publicly available in the BLS web schedule. To keep the
# scanner reliable, V0.1.1 uses this official 2026 schedule as a fallback for
# the macro releases that matter most to Gold Scanner.
# Dates/times are Eastern Time, as stated by BLS.
IMPORTANT_RELEASES_2026 = [
    # Employment Situation (NFP / unemployment)
    ("2026-01-09T08:30:00-05:00", "Employment Situation for December 2025"),
    ("2026-02-11T08:30:00-05:00", "Employment Situation for January 2026"),
    ("2026-03-06T08:30:00-05:00", "Employment Situation for February 2026"),
    ("2026-04-03T08:30:00-04:00", "Employment Situation for March 2026"),
    ("2026-05-08T08:30:00-04:00", "Employment Situation for April 2026"),
    ("2026-06-05T08:30:00-04:00", "Employment Situation for May 2026"),
    ("2026-07-02T08:30:00-04:00", "Employment Situation for June 2026"),
    ("2026-08-07T08:30:00-04:00", "Employment Situation for July 2026"),
    ("2026-09-04T08:30:00-04:00", "Employment Situation for August 2026"),
    ("2026-10-02T08:30:00-04:00", "Employment Situation for September 2026"),
    ("2026-11-06T08:30:00-05:00", "Employment Situation for October 2026"),
    ("2026-12-04T08:30:00-05:00", "Employment Situation for November 2026"),
    # CPI
    ("2026-01-13T08:30:00-05:00", "Consumer Price Index for December 2025"),
    ("2026-02-13T08:30:00-05:00", "Consumer Price Index for January 2026"),
    ("2026-03-11T08:30:00-04:00", "Consumer Price Index for February 2026"),
    ("2026-04-10T08:30:00-04:00", "Consumer Price Index for March 2026"),
    ("2026-05-12T08:30:00-04:00", "Consumer Price Index for April 2026"),
    ("2026-06-10T08:30:00-04:00", "Consumer Price Index for May 2026"),
    ("2026-07-14T08:30:00-04:00", "Consumer Price Index for June 2026"),
    ("2026-08-12T08:30:00-04:00", "Consumer Price Index for July 2026"),
    ("2026-09-11T08:30:00-04:00", "Consumer Price Index for August 2026"),
    ("2026-10-14T08:30:00-04:00", "Consumer Price Index for September 2026"),
    ("2026-11-10T08:30:00-05:00", "Consumer Price Index for October 2026"),
    ("2026-12-10T08:30:00-05:00", "Consumer Price Index for November 2026"),
    # PPI
    ("2026-01-14T08:30:00-05:00", "Producer Price Index for November 2025"),
    ("2026-01-30T08:30:00-05:00", "Producer Price Index for December 2025"),
    ("2026-02-27T08:30:00-05:00", "Producer Price Index for January 2026"),
    ("2026-03-18T08:30:00-04:00", "Producer Price Index for February 2026"),
    ("2026-04-14T08:30:00-04:00", "Producer Price Index for March 2026"),
    ("2026-05-13T08:30:00-04:00", "Producer Price Index for April 2026"),
    ("2026-06-11T08:30:00-04:00", "Producer Price Index for May 2026"),
    ("2026-07-15T08:30:00-04:00", "Producer Price Index for June 2026"),
    ("2026-08-13T08:30:00-04:00", "Producer Price Index for July 2026"),
    ("2026-09-10T08:30:00-04:00", "Producer Price Index for August 2026"),
    ("2026-10-15T08:30:00-04:00", "Producer Price Index for September 2026"),
    ("2026-11-13T08:30:00-05:00", "Producer Price Index for October 2026"),
    ("2026-12-15T08:30:00-05:00", "Producer Price Index for November 2026"),
    # JOLTS
    ("2026-01-07T10:00:00-05:00", "Job Openings and Labor Turnover Survey for November 2025"),
    ("2026-02-05T10:00:00-05:00", "Job Openings and Labor Turnover Survey for December 2025"),
    ("2026-03-13T10:00:00-04:00", "Job Openings and Labor Turnover Survey for January 2026"),
    ("2026-03-31T10:00:00-04:00", "Job Openings and Labor Turnover Survey for February 2026"),
    ("2026-05-05T10:00:00-04:00", "Job Openings and Labor Turnover Survey for March 2026"),
    ("2026-06-02T10:00:00-04:00", "Job Openings and Labor Turnover Survey for April 2026"),
    ("2026-06-30T10:00:00-04:00", "Job Openings and Labor Turnover Survey for May 2026"),
    ("2026-08-04T10:00:00-04:00", "Job Openings and Labor Turnover Survey for June 2026"),
    ("2026-09-01T10:00:00-04:00", "Job Openings and Labor Turnover Survey for July 2026"),
    ("2026-09-29T10:00:00-04:00", "Job Openings and Labor Turnover Survey for August 2026"),
    ("2026-11-03T10:00:00-05:00", "Job Openings and Labor Turnover Survey for September 2026"),
    ("2026-12-01T10:00:00-05:00", "Job Openings and Labor Turnover Survey for October 2026"),
]


def _unfold_ics(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def _parse_ics_date(value: str) -> datetime:
    value = value.split(":", 1)[-1].strip()
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if "T" in value:
        return datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=timezone.utc)


def _fallback_release_calendar() -> list[dict]:
    events = []
    for start, title in IMPORTANT_RELEASES_2026:
        dt = datetime.fromisoformat(start)
        events.append({
            "source": "BLS",
            "title": title,
            "start": dt.isoformat(),
            "uid": f"fallback-{dt.date().isoformat()}-{title}",
            "calendar_source": "official_2026_schedule_fallback",
        })
    return events


def fetch_release_calendar(timeout: int = 20) -> list[dict]:
    """Fetch BLS releases, with an official 2026 fallback for runner 403s."""
    headers = {
        "User-Agent": "GoldScanner/0.1.1 (+https://github.com/)",
        "Accept": "text/calendar,text/plain,*/*",
    }
    try:
        r = requests.get(BLS_ICS_URL, headers=headers, timeout=timeout)
        r.raise_for_status()
    except requests.RequestException:
        return _fallback_release_calendar()

    events = []
    current = {}
    in_event = False

    for line in _unfold_ics(r.text):
        if line == "BEGIN:VEVENT":
            current = {}
            in_event = True
        elif line == "END:VEVENT":
            if current.get("DTSTART") and current.get("SUMMARY"):
                events.append({
                    "source": "BLS",
                    "title": current["SUMMARY"],
                    "start": _parse_ics_date(current["DTSTART"]).isoformat(),
                    "uid": current.get("UID"),
                    "calendar_source": "bls_ics",
                })
            in_event = False
        elif in_event and ":" in line:
            key, value = line.split(":", 1)
            key = key.split(";", 1)[0]
            current[key] = value

    return events or _fallback_release_calendar()


def _request_batch(series_ids: list[str], startyear: str | None = None, endyear: str | None = None, timeout: int = 20) -> dict:
    """Fetch multiple BLS series in one API request.

    BLS officially supports POST requests with multiple series IDs. Using one
    batch request is important because the GitHub scanner runs periodically
    and the public BLS quota is request-based.
    """
    payload = {"seriesid": list(series_ids)}
    if startyear is not None:
        payload["startyear"] = str(startyear)
    if endyear is not None:
        payload["endyear"] = str(endyear)
    r = requests.post(
        BLS_API_URL,
        json=payload,
        timeout=timeout,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(data.get("message", ["Unknown BLS error"]))
    return data


def _rows_from_payload(payload: dict, limit: int | None = None) -> dict[str, list[dict]]:
    result = {}
    for series in payload.get("Results", {}).get("series", []):
        sid = series.get("seriesID")
        rows = []
        for item in series.get("data", []):
            try:
                rows.append({
                    "date": f"{item['year']}-{item['period'][1:]}",
                    "year": item["year"],
                    "period": item["period"],
                    "period_name": item.get("periodName"),
                    "value": float(item["value"]),
                })
            except (KeyError, ValueError, TypeError):
                continue
        result[sid] = rows[:limit] if limit else rows
    return result


def fetch_latest_series(series_id: str, timeout: int = 20) -> dict:
    """Fetch the latest observation for one series (kept for compatibility/tests)."""
    url = f"{BLS_API_URL}{series_id}"
    r = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    r.raise_for_status()
    payload = r.json()
    if payload.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(payload.get("message", ["Unknown BLS error"]))
    series = payload["Results"]["series"][0]
    data = series.get("data", [])
    if not data:
        raise RuntimeError(f"No BLS data returned for {series_id}")
    latest = data[0]
    return {
        "series_id": series_id,
        "year": latest["year"],
        "period": latest["period"],
        "period_name": latest.get("periodName"),
        "value": float(latest["value"]),
    }


def fetch_series_history(series_id: str, limit: int = 24, timeout: int = 20) -> list[dict]:
    """Fetch history for one series (compatibility helper)."""
    payload = _request_batch([series_id], timeout=timeout)
    return _rows_from_payload(payload, limit=limit).get(series_id, [])


def fetch_macro_history(timeout: int = 20) -> dict:
    """Fetch all Gold Scanner BLS series in a single request."""
    series_ids = list(SERIES.values())
    payload = _request_batch(series_ids, timeout=timeout)
    by_id = _rows_from_payload(payload, limit=24)
    return {name: by_id.get(series_id, []) for name, series_id in SERIES.items()}


def _observations_from_history(history: dict) -> dict:
    observations = {}
    for name, rows in history.items():
        if not rows:
            continue
        latest = rows[0]
        observations[name] = {
            "series_id": SERIES[name],
            "year": latest.get("year"),
            "period": latest.get("period"),
            "period_name": latest.get("period_name"),
            "value": latest.get("value"),
        }
    return observations


def fetch_v01_snapshot() -> dict:
    """Return BLS calendar + all latest observations with one API request."""
    calendar = fetch_release_calendar()
    history = fetch_macro_history()
    observations = _observations_from_history(history)
    return {
        "source": "BLS",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "calendar": calendar,
        "observations": observations,
        "history": history,
    }
