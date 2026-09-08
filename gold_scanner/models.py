from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class FactorReading:
    name: str
    score: float
    confidence: float
    direction: str
    reason: str
    observed_at: datetime

@dataclass
class ScannerState:
    macro_score: float = 0.0
    intraday_score: float = 0.0
    state: str = "INDECISION"
    previous_state: Optional[str] = None
    last_alert_key: Optional[str] = None
    updated_at: Optional[datetime] = None
    factors: list[FactorReading] = field(default_factory=list)
