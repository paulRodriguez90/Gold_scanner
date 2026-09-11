from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests


def _direction_emoji(bias: str) -> str:
    if "ALCISTA" in bias:
        return "🟢"
    if "BAJISTA" in bias:
        return "🔴"
    return "⚪"


def _confidence_emoji(confidence: str) -> str:
    return {"ALTA": "🟢", "MEDIA": "🟡", "BAJA": "⚪"}.get(confidence, "⚪")


def _score_gauge(score: float, width: int = 21) -> str:
    """Telegram score gauge with proportional position and intensity."""
    score = max(-100.0, min(100.0, float(score)))
    center = width // 2
    pos = int(round((score + 100.0) / 200.0 * (width - 1)))
    if score < -70:
        fill = "🟥"
    elif score < -30:
        fill = "🔴"
    elif score < 0:
        fill = "🟠"
    elif score > 70:
        fill = "🟩"
    elif score > 30:
        fill = "🟢"
    elif score > 0:
        fill = "🟡"
    else:
        fill = "⬜"
    cells = ["⬜"] * width
    cells[0] = "🔴"
    cells[center] = "│"
    cells[-1] = "🟢"
    if score < 0:
        for i in range(1, pos):
            cells[i] = fill
    elif score > 0:
        for i in range(center + 1, pos):
            cells[i] = fill
    if pos not in (0, center, width - 1):
        cells[pos] = "⚪"
    return "".join(cells)


def format_telegram_message(weekly_bias, daily_bias, next_event=None, retrieved_at=None) -> str:
    """Build the minimal directional-context message sent to Telegram."""
    if retrieved_at is None:
        retrieved_at = datetime.now(timezone.utc)
    elif retrieved_at.tzinfo is None:
        retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)

    art = retrieved_at.astimezone(ZoneInfo("America/Argentina/Buenos_Aires"))
    lines = [
        "══════════════════════════════",
        "🥇 GOLD SCANNER",
        "══════════════════════════════",
        "",
        "📅 SESGO SEMANAL",
        f"{_direction_emoji(weekly_bias.bias)} {weekly_bias.bias}",
        f"Confianza: {_confidence_emoji(weekly_bias.confidence)} {weekly_bias.confidence}",
        f"-100                                      +100",
        _score_gauge(weekly_bias.score),
        f"{' ' * (int(round((weekly_bias.score + 100.0) / 200.0 * 20)) * 2)}{weekly_bias.score:+.1f}",
        "",
        "📆 SESGO DEL DÍA",
        f"{_direction_emoji(daily_bias.bias)} {daily_bias.bias}",
        f"Confianza: {_confidence_emoji(daily_bias.confidence)} {daily_bias.confidence}",
        f"-100                                      +100",
        _score_gauge(daily_bias.score),
        f"{' ' * (int(round((daily_bias.score + 100.0) / 200.0 * 20)) * 2)}{daily_bias.score:+.1f}",
        "",
        "🧭 MOTIVO",
        daily_bias.reason,
    ]
    if next_event:
        lines.extend(["", "⚠️ RIESGO / EVENTO", str(next_event)])
    lines.extend([
        "",
        f"🕒 Actualizado: {art.strftime('%d/%m/%Y %H:%M')} ART",
        "",
        "ℹ️ Contexto direccional.",
        "Sin recomendación de compra/venta.",
        "══════════════════════════════",
    ])
    return "\n".join(lines)


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError("Telegram no configurado: faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=20)
    response.raise_for_status()
