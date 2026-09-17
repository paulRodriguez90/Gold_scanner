from datetime import datetime, timezone
from types import SimpleNamespace

from gold_scanner.telegram import format_telegram_message


def test_telegram_message_is_clean_and_contains_directional_context():
    weekly = SimpleNamespace(bias="SESGO BAJISTA MODERADO", confidence="MEDIA", score=-32.7, reason="Contexto macro bajista.")
    daily = SimpleNamespace(bias="SESGO BAJISTA DÉBIL", confidence="BAJA", score=-20.7, reason="Mercado en conflicto.")
    msg = format_telegram_message(weekly, daily, "CPI — 2026-09-11", datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc))
    assert "SESGO SEMANAL" in msg
    assert "SESGO BAJISTA MODERADO" in msg
    assert "SESGO DEL DÍA" in msg
    assert "SESGO BAJISTA DÉBIL" in msg
    assert "CPI — 2026-09-11" in msg
    assert "FUERZA DEL MERCADO" in msg
    assert "Sin recomendación" not in msg
    assert "-100" not in msg and "+100" not in msg
    assert "━" not in msg
    assert "🔴" in msg
    assert "🟠" not in msg
    assert "<b>Score: -32.7</b>" in msg and "<b>Score: -20.7</b>" in msg


def test_telegram_neutral_direction_uses_yellow():
    weekly = SimpleNamespace(bias="SESGO NEUTRAL", confidence="BAJA", score=0.0, reason="Sin dirección clara.")
    daily = SimpleNamespace(bias="SESGO ALCISTA DÉBIL", confidence="BAJA", score=12.0, reason="Momentum alcista.")
    msg = format_telegram_message(weekly, daily)
    assert "🟡 SESGO NEUTRAL" in msg
    assert "🟢 SESGO ALCISTA DÉBIL" in msg


def test_telegram_shows_only_force_classifications_for_timeframes():
    weekly = SimpleNamespace(bias="SESGO NEUTRAL", confidence="BAJA", score=0.0, reason="Mixto.")
    daily = SimpleNamespace(bias="SESGO ALCISTA MODERADO", confidence="MEDIA", score=40.0, reason="Contexto.")
    technical = {"5H": SimpleNamespace(classification="ALCISTA FUERTE"), "1H": SimpleNamespace(classification="BAJISTA DÉBIL")}
    msg = format_telegram_message(weekly, daily, technical=technical)
    assert "5H: 🟢 ALCISTA FUERTE" in msg
    assert "1H: 🔴 BAJISTA DÉBIL" in msg
