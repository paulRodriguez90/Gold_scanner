from datetime import datetime, timezone
from types import SimpleNamespace

from gold_scanner.telegram import format_telegram_message


def test_telegram_message_contains_directional_context():
    weekly = SimpleNamespace(bias="SESGO BAJISTA MODERADO", confidence="MEDIA", score=-32.7, reason="Contexto macro bajista.")
    daily = SimpleNamespace(bias="SESGO BAJISTA DÉBIL", confidence="BAJA", score=-20.7, reason="Mercado en conflicto.")
    msg = format_telegram_message(weekly, daily, "CPI — 2026-09-11", datetime(2026, 9, 10, 17, 0, tzinfo=timezone.utc))
    assert "SESGO SEMANAL" in msg
    assert "SESGO BAJISTA MODERADO" in msg
    assert "SESGO DEL DÍA" in msg
    assert "SESGO BAJISTA DÉBIL" in msg
    assert "CPI — 2026-09-11" in msg
    assert "Sin recomendación de compra/venta." in msg
    assert "-100" in msg and "+100" in msg
    assert "🔴" in msg and "🟢" in msg
    gauges = [line for line in msg.splitlines() if line.startswith("🔴") and line.endswith("🟢")]
    assert len(gauges) == 2
    assert all(len(line) < 45 for line in gauges)
    assert "-32.7" in msg and "-20.7" in msg
