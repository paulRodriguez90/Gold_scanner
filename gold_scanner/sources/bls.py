from __future__ import annotations

from datetime import datetime, timezone
import re
import requests

BLS_ICS_URL = "https://www.bls.gov/schedule/news_release/bls.ics"
BLS_API_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"

# Official BLS series used by the scanner in V0.1.
SERIES = {
    "cpi_all_items": "CUUR0000SA0",
    "ppi_final_demand": "WPSFD4",
    "unemployment_rate": "LNS14000000",
    "nonfarm_payrolls": "CES0000000001",
}


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


def fetch_release_calendar(timeout: int = 20) -> list[dict]:
    """Fetch upcoming BLS releases from the official BLS calendar."""
    r = requests.get(BLS_ICS_URL, timeout=timeout)
    r.raise_for_status()

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
                })
            in_event = False
        elif in_event and ":" in line:
            key, value = line.split(":", 1)
            key = key.split(";", 1)[0]
            current[key] = value

    return events


def fetch_latest_series(series_id: str, timeout: int = 20) -> dict:
    """Fetch the latest observation from the public BLS API v1."""
    r = requests.get(
        BLS_API_URL,
        params={"series_id": series_id},
        timeout=timeout,
    )
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


def fetch_v01_snapshot() -> dict:
    """Return the V0.1 BLS snapshot: calendar + latest core observations."""
    calendar = fetch_release_calendar()
    observations = {
        name: fetch_latest_series(series_id)
        for name, series_id in SERIES.items()
    }

    return {
        "source": "BLS",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "calendar": calendar,
        "observations": observations,
    }
