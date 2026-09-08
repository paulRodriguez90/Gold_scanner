from .scoring import classify

def should_alert(previous_score: float, current_score: float, previous_state: str, current_state: str) -> bool:
    # Alert on meaningful score movement or state transition.
    return abs(current_score - previous_score) >= 20 or previous_state != current_state

def build_bias_change(previous_score: float, current_score: float, reasons: list[str]) -> str:
    return (
        "🚨 GOLD SCANNER — CAMBIO DE SESGO\n\n"
        f"Anterior: {previous_score:+.0f} ({classify(previous_score)})\n"
        f"Actual:   {current_score:+.0f} ({classify(current_score)})\n\n"
        "Motivos:\n" + "\n".join(f"• {r}" for r in reasons)
    )
