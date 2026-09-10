from __future__ import annotations

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests


def _direction_emoji(bias: str) -> str:
    if "ALCISTA" in bias:
        if "FUERTE" in bias:
            return "🟢"
        if "MODERADO" in bias:
            return "🟢"
        return "🟡"
    if "BAJISTA" in bias:
        if "FUERTE" in bias:
            return "🔴"
        if "MODERADO" in bias:
            return "🔴"
        return "🟠"
    return "⚪"


def _confidence_emoji(confidence: str) -> str:
    return {"ALTA": "🟢", "MEDIA": "🟡", "BAJA": "⚪"}.get(confidence, "⚪")


def format_telegram_message(weekly_bias, daily_bias, next_event=None, retrieved_at=None) -> str:
    """Build the concise directional-context message sent to Telegram."""
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
        f"Score: {weekly_bias.score:+.1f}",
        "",
        "📆 SESGO DEL DÍA",
        f"{_direction_emoji(daily_bias.bias)} {daily_bias.bias}",
        f"Confianza: {_confidence_emoji(daily_bias.confidence)} {daily_bias.confidence}",
        f"Score: {daily_bias.score:+.1f}",
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
        "ℹ️ Contexto direccional. Sin recomendación de compra/venta.",
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
