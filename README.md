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


## V0.3.2 — último dato disponible
- Los factores de mercado usan siempre la observación más reciente disponible cuya fecha sea hoy o anterior.
- Si el dato del día todavía no fue publicado, se utiliza automáticamente el último día hábil disponible.
- Esto cubre fines de semana y feriados: por ejemplo, sábado/domingo utiliza el viernes.
- El reporte identifica la frescura: `actual` o `dato anterior (YYYY-MM-DD)`.
- Las observaciones futuras se ignoran.
- Para Treasury se buscan el mes actual y el anterior; FRED sigue como fallback para Real Yield si Treasury no responde.
