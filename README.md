# Gold Scanner

Independent macro-bias assistant for manual XAUUSD trading.

## Purpose
The scanner monitors macroeconomic, market and gold-specific variables and sends alerts when:
- the weekly/intraday bias changes,
- a high-impact event is released,
- a relevant event is approaching,
- macro variables conflict,
- the scheduled weekly or NY report is due.

It does **not** execute trades and is intentionally independent from BotLion, Mina de Oro, Virutas de Oro and other EAs.

## Initial architecture
Data sources -> normalization -> factor scores -> correlation/conflict layer -> Gold Score -> state -> alert engine -> Telegram.

## Initial factor groups
- Fed
- Inflation
- Employment
- DXY
- US10Y
- Real Yields
- China
- PBoC / central-bank gold demand
- Oil
- Geopolitics
- XAUUSD

## Status
V0 implementation scaffold. Data connectors and credentials are intentionally isolated from the scoring engine.
