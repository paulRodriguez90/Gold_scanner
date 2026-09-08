from datetime import datetime, timezone


def _fmt_change(value, unit):
    if value is None:
        return "n/a"
    return f"{value:+.3f}{' pp' if unit == '%' else '%'}"


def print_v02_report(fed, bls, markets):
    print("=== GOLD SCANNER V0.2 — DXY / US10Y / REAL YIELDS / XAUUSD ===")
    print(f"Retrieved: {datetime.now(timezone.utc).isoformat()}")
    print("\nMARKET DRIVERS")
    for key in ("dxy", "us10y", "real_yields", "xauusd"):
        r = markets[key]
        print(f"{r.name}: {r.value:.4f} {r.unit} | 1d {_fmt_change(r.change_1d, r.unit)} | 5d {_fmt_change(r.change_5d, r.unit)}")
        print(f"  -> {r.direction} | score={r.score:+.1f} | source={r.source}")
    print("\nFED")
    # fetch_v01_snapshot() stores the target range as a nested object.
    # Keep the report aligned with that contract instead of assuming flat keys.
    target = fed.get("target_range", {})
    lower = target.get("lower")
    upper = target.get("upper")
    target_date = target.get("date")
    if lower is not None and upper is not None:
        print(f"Target range: {lower:.2f}% - {upper:.2f}%")
    else:
        print("Target range: unavailable")
    print(f"Effective data date: {target_date or 'unavailable'}")
    print("\nBLS LATEST OBSERVATIONS")
    observations = bls.get("observations", bls.get("latest", {}))
    for name, value in observations.items():
        if isinstance(value, dict):
            period = value.get("period_name") or value.get("period") or ""
            year = value.get("year", "")
            shown = value.get("value", "n/a")
            suffix = f" ({period} {year})" if (period or year) else ""
            print(f"{name}: {shown}{suffix}")
        else:
            print(f"{name}: {value}")

    print("\nUPCOMING BLS RELEASES")
    releases = bls.get("upcoming_releases", bls.get("calendar", []))
    for item in releases[:6]:
        if "date" in item:
            label = f"{item['date']} {item.get('time', '')} ET".strip()
        else:
            start = item.get("start", "")
            label = start.replace("T", " ")[:16]
        print(f"- {label} — {item.get('title', item.get('summary', ''))}")
