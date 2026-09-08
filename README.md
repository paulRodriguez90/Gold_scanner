# Gold Scanner V0.5

Scanner macro/market para XAUUSD. No ejecuta operaciones.

## V0.5

Agrega **Actual vs Consensus** para CPI, Core CPI, PPI, NFP y desempleo.

- Trading Economics es la fuente preferida para consenso y actual.
- Si existe `TRADING_ECONOMICS_API_KEY`, se usa la API.
- Sin API key, se intenta la página pública del indicador como fallback.
- Si no hay consenso, el scanner **no inventa** un forecast y no calcula surprise para ese evento.
- Surprise score:
  - CPI/Core CPI/PPI por debajo del consenso: favorable al oro.
  - NFP por debajo del consenso: favorable al oro.
  - Desempleo por encima del consenso: favorable al oro.
- El score combinado pasa a ser:
  - 55% Market Confluence
  - 25% Macro Fundamental
  - 20% Consensus Surprise

## Fuentes

- BLS: CPI, Core CPI, PPI, Core PPI, NFP, desempleo.
- Federal Reserve: rango objetivo y calendario FOMC.
- Yahoo / Treasury / FRED / Trading Economics / XAUS: mercado.
- Trading Economics: consenso económico y actualizaciones de calendario.

## Ejecución

```bash
python -m pytest -q
python -m gold_scanner.main
```

## Nota

La reacción posterior al dato intradía queda preparada como siguiente capa. V0.5 no usa una reacción inventada ni sustituye consenso faltante por estimaciones propias.
