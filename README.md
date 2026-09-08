# Gold Scanner

## V0.3 — Market Confluence

V0.3 turns the four connected market drivers into a **confluence layer** instead of simply adding their scores.

### Logic

- **DXY, US10Y and 10Y real yield** form the macro-pressure block.
- **XAUUSD** is treated separately as price confirmation.
- If macro pressure and XAUUSD disagree, the scanner does **not** issue a clean buy/sell state; it moves to `ALCISTA — ESPERAR` or `BAJISTA — ESPERAR` and marks the conflict.
- If macro drivers themselves strongly disagree, the scanner also marks a conflict.
- Unavailable sources are ignored in the macro-pressure average rather than being converted into an artificial signal.

### Output

The report now shows:

- Macro pressure: -100 to +100
- XAUUSD confirmation: -100 to +100
- Confluence score: -100 to +100
- Conflict and conflict level
- Final market reading
- Human-readable explanation of why the scanner is waiting or confirming

This is still **not a complete trading signal**. Fed, inflation, employment, China/PBoC, geopolitics, news surprise and reaction analysis remain separate layers to be integrated.

## Run locally

```bash
pip install -r requirements.txt
python -m pytest -q
python -m gold_scanner.main
```
