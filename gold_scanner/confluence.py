from dataclasses import dataclass
from typing import Mapping

from .config import ScannerConfig


@dataclass(frozen=True)
class MarketConfluence:
    macro_pressure: float
    xau_confirmation: float
    score: float
    state: str
    conflict: bool
    conflict_level: str
    explanation: str
    available_macro_factors: int
    missing_macro_factors: tuple[str, ...]


def _clamp(value: float, low: float = -100.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def _sign(value: float, deadband: float = 10.0) -> int:
    if value > deadband:
        return 1
    if value < -deadband:
        return -1
    return 0


def _reading_score(readings: Mapping[str, object], name: str) -> float | None:
    reading = readings.get(name)
    if reading is None:
        return None
    value = getattr(reading, "score", None)
    if value is None:
        return None
    source = getattr(reading, "source", "")
    # An unavailable source must never become artificial bullish/bearish pressure.
    if source == "UNAVAILABLE":
        return None
    return _clamp(value)


def calculate_market_confluence(readings: Mapping[str, object]) -> MarketConfluence:
    """Interpret DXY, nominal yield and real yield as macro pressure.

    XAUUSD is deliberately kept separate as a confirmation signal. We do not
    simply add the four factor scores: a bullish macro backdrop with a falling
    gold price is treated as a wait/conflict condition, not as a clean buy.
    """
    macro_components = {
        "dxy": (35.0, _reading_score(readings, "dxy")),
        "us10y": (30.0, _reading_score(readings, "us10y")),
        "real_yields": (35.0, _reading_score(readings, "real_yields")),
    }
    available = [(name, weight, score) for name, (weight, score) in macro_components.items() if score is not None]
    missing = tuple(name for name, (_, score) in macro_components.items() if score is None)
    if available:
        macro_pressure = sum(weight * score for _, weight, score in available) / sum(weight for _, weight, _ in available)
    else:
        macro_pressure = 0.0

    xau = _reading_score(readings, "xauusd")
    xau_confirmation = xau if xau is not None else 0.0

    macro_sign = _sign(macro_pressure)
    xau_sign = _sign(xau_confirmation)

    direct_conflict = False
    conflict_reasons: list[str] = []

    # Conflict inside the three macro drivers.
    macro_scores = [score for _, _, score in available]
    if macro_scores and max(macro_scores) >= 25 and min(macro_scores) <= -25:
        direct_conflict = True
        conflict_reasons.append("los drivers macro están divididos")

    # Price confirmation conflict.
    if macro_sign != 0 and xau_sign != 0 and macro_sign != xau_sign:
        direct_conflict = True
        conflict_reasons.append("XAUUSD no confirma la presión macro")

    # XAU confirmation has a smaller numerical role than macro pressure.
    # It can strengthen a confirmed move, but cannot erase a meaningful macro conflict.
    score = _clamp(0.80 * macro_pressure + 0.20 * xau_confirmation)

    # A missing core macro driver reduces confidence. We still calculate the
    # available pressure, but we never turn incomplete data into a strong
    # actionable state.
    incomplete = len(missing) > 0

    def _wait_state(direction: int, force_conflict: bool = False) -> str:
        prefix = "ALCISTA" if direction > 0 else "BAJISTA"
        # Missing core data means the missing macro driver is the next thing
        # that must confirm the direction.
        if incomplete:
            missing_text = ", ".join(missing)
            return f"{prefix} — ESPERAR CONFIRMACIÓN MACRO ({missing_text})"
        # If the macro drivers conflict internally, or price disagrees with
        # the macro block, the next useful event is resolution of that conflict.
        if force_conflict or (macro_sign != 0 and xau_sign != 0 and macro_sign != xau_sign):
            return f"{prefix} — ESPERAR RESOLUCIÓN DEL CONFLICTO"
        # Macro has a direction but XAUUSD is not confirming it yet.
        if xau_sign == 0:
            return f"{prefix} — ESPERAR CONFIRMACIÓN DE PRECIO"
        # Fallback for a weak directional score.
        return f"{prefix} — DÉBIL"

    if abs(macro_pressure) < 15:
        state = "INDECISION"
    elif direct_conflict:
        state = _wait_state(1 if macro_pressure > 0 else -1, force_conflict=True)
    elif macro_pressure >= 60 and xau_sign >= 0:
        state = "COMPRA FUERTE"
    elif macro_pressure >= 30:
        state = "COMPRA MODERADA" if xau_sign > 0 else _wait_state(1)
    elif macro_pressure <= -60 and xau_sign <= 0:
        state = "VENTA FUERTE"
    elif macro_pressure <= -30:
        state = "VENTA MODERADA" if xau_sign < 0 else _wait_state(-1)
    else:
        state = _wait_state(1 if macro_pressure > 0 else -1)

    if incomplete and state in {"COMPRA FUERTE", "COMPRA MODERADA"}:
        state = _wait_state(1)
    elif incomplete and state in {"VENTA FUERTE", "VENTA MODERADA"}:
        state = _wait_state(-1)

    if direct_conflict:
        conflict_level = "ALTO" if len(conflict_reasons) > 1 else "MEDIO"
    else:
        conflict_level = "NINGUNO"

    if state.startswith("COMPRA"):
        explanation = "La presión macro favorece al oro y XAUUSD confirma o no contradice el movimiento."
    elif state.startswith("VENTA"):
        explanation = "La presión macro pesa sobre el oro y XAUUSD confirma o no contradice el movimiento."
    elif direct_conflict:
        explanation = "; ".join(conflict_reasons) + ". Se necesita resolver el conflicto antes de una señal operable."
    elif "CONFIRMACIÓN DE PRECIO" in state:
        explanation = "La presión macro tiene dirección, pero XAUUSD todavía no confirma el movimiento."
    elif "CONFIRMACIÓN MACRO" in state:
        explanation = "La dirección existe, pero falta un driver macro clave para confirmar la lectura."
    elif "DÉBIL" in state:
        explanation = "La dirección existe, pero la intensidad de la confluencia todavía es débil."
    elif macro_sign > 0:
        explanation = "La presión macro es favorable al oro, pero la confluencia todavía no es suficiente para una señal fuerte."
    elif macro_sign < 0:
        explanation = "La presión macro es desfavorable al oro, pero la confluencia todavía no es suficiente para una señal fuerte."
    else:
        explanation = "Los drivers disponibles no muestran una dirección macro clara."

    if incomplete:
        missing_text = ", ".join(missing)
        explanation += f" Datos incompletos: falta {missing_text}."

    return MarketConfluence(
        macro_pressure=round(macro_pressure, 1),
        xau_confirmation=round(xau_confirmation, 1),
        score=round(score, 1),
        state=state,
        conflict=direct_conflict,
        conflict_level=conflict_level,
        explanation=explanation,
        available_macro_factors=len(available),
        missing_macro_factors=missing,
    )
