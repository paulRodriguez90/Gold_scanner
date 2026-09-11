# Gold Scanner V0.7.3

Scanner direccional para contexto manual de XAUUSD. No ejecuta operaciones.

## V0.7.3
- Sesgo semanal y diario.
- MACD 1H + Estocástico 1H como contexto técnico interno del sesgo diario.
- Solo velas 1H cerradas para evitar repainting.
- Los indicadores técnicos no se muestran en Telegram.
- Telegram minimalista con score -100/+100 y gauge visual por intensidad.
- Cada nueva publicación macro reemplaza el dato vigente de ese mismo indicador/métrica; no se acumulan publicaciones antiguas del mismo indicador.
- Telegram mantiene únicamente el resultado final: sesgo semanal, sesgo diario, motivo, riesgo/evento, hora y disclaimer.

## Ejecución
```bash
python -m pytest -q
python -m gold_scanner.main
```

Variables de entorno para Telegram:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
