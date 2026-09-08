from datetime import datetime, timezone


def _fmt_change(value, unit):
    if value is None:
        return "n/a"
    return f"{value:+.3f}{' pp' if unit == '%' else '%'}"


def print_v03_report(fed, bls, markets, confluence):
    print("=== GOLD SCANNER V0.3 — MARKET CONFLUENCE ===")
    print(f"Retrieved: {datetime.now(timezone.utc).isoformat()}")
    print("\nMARKET DRIVERS")
    for key in ("dxy", "us10y", "real_yields", "xauusd"):
        r = markets[key]
        value = "n/a" if r.value is None else f"{r.value:.4f}"
        print(f"{r.name}: {value} {r.unit} | 1d {_fmt_change(r.change_1d, r.unit)} | 5d {_fmt_change(r.change_5d, r.unit)}")
        print(f"  -> {r.direction} | score={r.score:+.1f} | source={r.source}")

    print("\nMARKET CONFLUENCE")
    print(f"Macro pressure (DXY/US10Y/Real Yield): {confluence.macro_pressure:+.1f}")
    print(f"XAUUSD confirmation: {confluence.xau_confirmation:+.1f}")
    print(f"Confluence score: {confluence.score:+.1f}")
    print(f"Conflict: {'YES' if confluence.conflict else 'NO'} | level={confluence.conflict_level}")
    print(f"Reading: {confluence.state}")
    print(f"Why: {confluence.explanation}")

    print("\nFED")
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

    print("\nV0.3 STATUS: MARKET CONFLUENCE ACTIVE; MACRO NEWS SCORING STILL IN PROGRESS.")

# Backward-compatible entry point retained for existing tests/tools.
def print_v02_report(fed, bls, markets):
    from .confluence import calculate_market_confluence
    confluence = calculate_market_confluence(markets)
    print_v03_report(fed, bls, markets, confluence)
