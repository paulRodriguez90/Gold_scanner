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
    print(f"Target range: {fed['target_lower']:.2f}% - {fed['target_upper']:.2f}%")
    print(f"Effective data date: {fed['target_date']}")
    print("\nBLS LATEST OBSERVATIONS")
    for name, value in bls["latest"].items():
        print(f"{name}: {value}")
    print("\nUPCOMING BLS RELEASES")
    for item in bls["upcoming_releases"][:6]:
        print(f"- {item['date']} {item['time']} ET — {item['title']}")
