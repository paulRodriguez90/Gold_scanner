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


def _score_gauge(score: float, width: int = 16) -> str:
    """Single-line compact score scale for Telegram.

    The left endpoint is red (-100) and the marker moves with the score.
    The right endpoint is represented by the +100 label above the line.
    """
    score = max(-100.0, min(100.0, float(score)))
    pos = int(round((score + 100.0) / 200.0 * width))

    if score <= -70:
        marker = "🔴"
    elif score < -30:
        marker = "🟠"
    elif score < 0:
        marker = "🟡"
    elif score >= 70:
        marker = "🟢"
    elif score > 30:
        marker = "🟢"
    elif score > 0:
        marker = "🟡"
    else:
        marker = "⚪"

    pos = min(width, max(0, pos))
    return "🔴" + ("━" * pos) + marker + ("━" * max(0, width - pos))


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
        f"<b>Score: {weekly_bias.score:+.1f}</b>",
        "",
        "📆 SESGO DEL DÍA",
        f"{_direction_emoji(daily_bias.bias)} {daily_bias.bias}",
        f"Confianza: {_confidence_emoji(daily_bias.confidence)} {daily_bias.confidence}",
        f"-100                                      +100",
        _score_gauge(daily_bias.score),
        f"<b>Score: {daily_bias.score:+.1f}</b>",
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
    response = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=20)
    response.raise_for_status()
