from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DirectionalBias:
    score: float
    bias: str
    confidence: str
    reason: str


def clamp(value: float, low: float = -100.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def classify_bias(score: float) -> tuple[str, str]:
    score = clamp(score)
    strength = abs(score)
    if strength < 10:
        return "SESGO NEUTRAL", "BAJA"
    direction = "ALCISTA" if score > 0 else "BAJISTA"
    if strength >= 60:
        return f"SESGO {direction} FUERTE", "ALTA"
    if strength >= 30:
        return f"SESGO {direction} MODERADO", "MEDIA"
    return f"SESGO {direction} DÉBIL", "BAJA"


def build_bias(score: float, reason: str) -> DirectionalBias:
    bias, confidence = classify_bias(score)
    return DirectionalBias(round(clamp(score), 1), bias, confidence, reason)


def _factor_reason(macro) -> str:
    factors = list(getattr(macro, "factors", ()) or ())
    if not factors:
        return "No hay factores fundamentales suficientes para explicar el sesgo."
    strongest = max(factors, key=lambda f: abs(float(f.score)))
    return f"{strongest.name} es el factor fundamental dominante ({strongest.direction.lower()}, {strongest.score:+.1f})."


def build_weekly_bias(macro, surprise: dict | None, next_event: str | None = None) -> DirectionalBias:
    # Weekly context intentionally emphasizes slower-moving fundamentals.
    # Surprise is included as recent information, while intraday market price
    # is not allowed to dominate the weekly bias.
    macro_score = float(getattr(macro, "score", 0.0))
    surprise_score = float((surprise or {}).get("score", 0.0))
    score = clamp(0.70 * macro_score + 0.30 * surprise_score)
    reason = _factor_reason(macro)
    if surprise_score > 10:
        reason += " Las últimas sorpresas macro favorecen al oro."
    elif surprise_score < -10:
        reason += " Las últimas sorpresas macro pesan sobre el oro."
    else:
        reason += " Las últimas sorpresas macro son mixtas o leves."
    if next_event:
        reason += f" Evento relevante próximo: {next_event}."
    return build_bias(score, reason)


def build_daily_bias(combined_score: float, confluence, macro, surprise: dict | None, next_event: str | None = None, technical=None) -> DirectionalBias:
    score = clamp(combined_score)
    market_score = float(getattr(confluence, "score", 0.0))
    macro_score = float(getattr(macro, "score", 0.0))
    surprise_score = float((surprise or {}).get("score", 0.0))
    parts = []
    if abs(market_score) >= max(abs(macro_score), abs(surprise_score), 10):
        parts.append("el mercado es el factor dominante")
    elif abs(macro_score) >= max(abs(market_score), abs(surprise_score), 10):
        parts.append("el contexto fundamental es el factor dominante")
    elif abs(surprise_score) >= 10:
        parts.append("las últimas sorpresas macro son el factor dominante")
    else:
        parts.append("los factores están equilibrados")
    if getattr(confluence, "conflict", False):
        parts.append("existe conflicto entre los drivers y el precio")
    if technical is not None:
        tech_direction = getattr(technical, "direction", "NEUTRAL")
        if tech_direction == "ALCISTA" and score > 0:
            parts.append("el contexto técnico 1H acompaña")
        elif tech_direction == "BAJISTA" and score < 0:
            parts.append("el contexto técnico 1H acompaña")
        elif tech_direction != "NEUTRAL" and ((tech_direction == "ALCISTA" and score < 0) or (tech_direction == "BAJISTA" and score > 0)):
            parts.append("existe conflicto con el contexto técnico 1H")
    reason = "; ".join(parts).capitalize() + "."
    if next_event:
        reason += f" Evento relevante próximo: {next_event}."
    return build_bias(score, reason)
