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
    """Calculate the global score against the full configured weight set.

    Missing factors contribute 0 (neutral); they do not cause the known
    factors to be re-normalized upward.
    """
    total_weight = sum(ScannerConfig.factor_weights.values())
    if not total_weight:
        return 0.0

    total = 0.0
    for name, weight in ScannerConfig.factor_weights.items():
        score = clamp(factor_scores.get(name, 0.0))
        total += score * weight

    return clamp(total / total_weight)
