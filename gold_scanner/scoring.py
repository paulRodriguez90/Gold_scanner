from .config import ScannerConfig

STATES = [
    (70, "COMPRA FUERTE"),
    (30, "COMPRA MODERADA"),
    (10, "ALCISTA — ESPERAR"),
    (-10, "INDECISION"),
    (-30, "BAJISTA — ESPERAR"),
    (-70, "VENTA MODERADA"),
    (-101, "VENTA FUERTE"),
]

def clamp(value: float, low=-100.0, high=100.0):
    return max(low, min(high, value))

def classify(score: float) -> str:
    for threshold, label in STATES:
        if score >= threshold:
            return label
    return "VENTA FUERTE"

def weighted_score(factor_scores: dict[str, float]) -> float:
    total = 0.0
    weight_total = 0.0
    for name, weight in ScannerConfig.factor_weights.items():
        if name in factor_scores:
            total += clamp(factor_scores[name]) * weight
            weight_total += weight
    return clamp(total / weight_total if weight_total else 0.0)
