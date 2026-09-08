from __future__ import annotations

from datetime import datetime, timezone


def print_v01_report(fed: dict, bls: dict) -> None:
    print("\n=== GOLD SCANNER V0.1 — REAL DATA CHECK ===")
    print(f"Retrieved: {datetime.now(timezone.utc).isoformat()}")

    target = fed["target_range"]
    print("\nFED")
    print(f"Target range: {target['lower']:.2f}% - {target['upper']:.2f}%")
    print(f"Effective data date: {target['date']}")

    print("\nNEXT FOMC")
    for meeting in fed["fomc_2026"]:
        if meeting["month"] == "September":
            print(
                f"September {meeting['start_day']}-{meeting['end_day']}, "
                f"{meeting['year']}  <-- next scheduled 2026 meeting"
            )
        else:
            print(
                f"{meeting['month']} {meeting['start_day']}-{meeting['end_day']}, "
                f"{meeting['year']}"
            )

    print("\nBLS LATEST OBSERVATIONS")
    for name, obs in bls["observations"].items():
        print(
            f"{name}: {obs['value']} "
            f"({obs['year']} {obs['period_name']})"
        )

    print("\nUPCOMING BLS RELEASES")
    important = ("Consumer Price Index", "Producer Price Index", "Employment Situation")
    count = 0
    for event in bls["calendar"]:
        if any(term in event["title"] for term in important):
            print(f"{event['start']} | {event['title']}")
            count += 1
        if count >= 12:
            break
