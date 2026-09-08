from dataclasses import dataclass

@dataclass(frozen=True)
class ScannerConfig:
    weekly_weight: float = 0.40
    intraday_weight: float = 0.60
    alert_score_change: float = 20.0
    high_impact_minutes: int = 60

    # Factor weights sum to 100.
    factor_weights = {
        "fed": 18,
        "inflation": 14,
        "employment": 10,
        "dxy": 12,
        "us10y": 10,
        "real_yields": 12,
        "china": 6,
        "pboc": 5,
        "oil": 4,
        "geopolitics": 4,
        "xauusd": 5,
    }
