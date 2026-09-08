from datetime import datetime, timezone


def _fmt_change(value, unit):
    if value is None:
        return "n/a"
    return f"{value:+.3f}{' pp' if unit == '%' else '%'}"


def print_v03_report(fed, bls, markets, confluence, macro=None, combined_score=None, surprise=None):
    print("=== GOLD SCANNER V0.6 — PERSISTENT MACRO CONTEXT ===")
    print(f"Retrieved: {datetime.now(timezone.utc).isoformat()}")
    print("\nMARKET DRIVERS")
    for key in ("dxy", "us10y", "real_yields", "xauusd"):
        r = markets[key]
        value = "n/a" if r.value is None else f"{r.value:.4f}"
        observed_date = r.observed_at.date().isoformat() if r.observed_at else None
        today = datetime.now(timezone.utc).date().isoformat()
        freshness = "actual" if observed_date == today else f"dato anterior ({observed_date})" if observed_date else "fecha desconocida"
        print(f"{r.name}: {value} {r.unit} | 1d {_fmt_change(r.change_1d, r.unit)} | 5d {_fmt_change(r.change_5d, r.unit)}")
        print(f"  -> {r.direction} | score={r.score:+.1f} | {freshness} | source={r.source}")

    print("\nMARKET CONFLUENCE")
    print(f"Macro pressure (DXY/US10Y/Real Yield): {confluence.macro_pressure:+.1f}")
    print(f"XAUUSD confirmation: {confluence.xau_confirmation:+.1f}")
    print(f"Macro data coverage: {confluence.available_macro_factors}/3")
    if confluence.missing_macro_factors:
        print(f"Missing macro factors: {', '.join(confluence.missing_macro_factors)}")
    print(f"Confluence score: {confluence.score:+.1f}")
    print(f"Conflict: {'YES' if confluence.conflict else 'NO'} | level={confluence.conflict_level}")
    print(f"Reading: {confluence.state}")
    print(f"Why: {confluence.explanation}")

    if macro is not None:
        print("\nMACRO FUNDAMENTAL IMPACT")
        print(f"Macro score (CPI/PPI + Employment + Fed): {macro.score:+.1f}")
        print(f"Macro reading: {macro.state}")
        for factor in macro.factors:
            date_text = factor.data_date or "n/a"
            print(f"{factor.name}: {factor.score:+.1f} -> {factor.direction} | {factor.reason} | date={date_text}")
        if macro.next_fomc:
            print(f"Next FOMC: {macro.next_fomc}")
        print(f"Macro explanation: {macro.explanation}")
        if surprise is not None:
            print("\nCONSENSUS SURPRISE IMPACT")
            print(f"Active surprise score: {surprise["score"]:+.1f}")
            print(f"Active surprise reading: {surprise["state"]}")
            for row in surprise.get("events", []):
                print(f"{row["label"]}: actual={row["actual"]} | consensus={row["consensus"]} | previous={row.get("previous")} | surprise={row["surprise"]:+.4g} | score={row["score"]:+.1f} | date={row["date"]} | source={row.get('source','n/a')}")
            upcoming = [e for e in (surprise.get("upcoming", []) or []) if e.get("consensus") is not None]
            if upcoming:
                print("Upcoming consensus:")
                for row in upcoming[:6]:
                    print(f"{row["label"]}: consensus={row["consensus"]} | previous={row.get("previous")} | date={row["date"]} | source={row.get('source','n/a')}")
            print(f"Surprise explanation: {surprise["explanation"]}")
            print("Nota: el último surprise válido permanece en la ecuación hasta que exista una publicación más reciente del mismo indicador/métrica.")
        if combined_score is not None:
            print(f"Combined score (55% market / 25% macro / 20% surprise): {combined_score:+.1f}")

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
    now = datetime.now(timezone.utc)
    future = []
    for item in releases:
        raw = item.get("start") or item.get("date")
        if not raw:
            continue
        try:
            if "T" in raw:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            else:
                dt = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            if dt > now:
                future.append((dt, item))
        except ValueError:
            continue
    future.sort(key=lambda x: x[0])
    for dt, item in future[:6]:
        local_label = dt.strftime("%Y-%m-%d %H:%M UTC")
        print(f"- {local_label} — {item.get('title', item.get('summary', ''))}")

    print("\nV0.5.3 STATUS: MARKET CONFLUENCE + MACRO FUNDAMENTAL + NORMALIZED CONSENSUS SURPRISE SCORING ACTIVE.")

# Backward-compatible entry point retained for existing tests/tools.
def print_v02_report(fed, bls, markets):
    from .confluence import calculate_market_confluence
    confluence = calculate_market_confluence(markets)
    print_v03_report(fed, bls, markets, confluence)
