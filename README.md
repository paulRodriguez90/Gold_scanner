# Gold Scanner V0.7.4

Scanner direccional para contexto manual de XAUUSD. No ejecuta operaciones.

## V0.7.4
- Sesgo semanal y diario.
- Fuerza técnica interna de XAUUSD spot en 5H (continuidad) y 1H (presión reciente), usando solo velas cerradas.
- Composite agrupado: tendencia por medias, momentum y variación; no sobrepondera indicadores correlacionados.
- No usa GC futures como sustituto del cálculo técnico.
- Los indicadores técnicos no se muestran en Telegram.
- Telegram minimalista con score -100/+100 y gauge visual por intensidad.
- Cada nueva publicación macro reemplaza el dato vigente de ese mismo indicador/métrica; no se acumulan publicaciones antiguas del mismo indicador.
- Telegram mantiene únicamente el resultado final: sesgo semanal, sesgo diario, fuerza 5H/1H, motivo, riesgo/evento y hora.

## Ejecución
```bash
python -m pytest -q
python -m gold_scanner.main
```

Variables de entorno para Telegram:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
