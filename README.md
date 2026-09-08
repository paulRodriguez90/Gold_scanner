# Gold Scanner V0.5.3

Scanner macro/market para XAUUSD. No ejecuta operaciones.

## V0.5.3

Mejora la capa de **Actual vs Consensus**:
- Trading Economics API si existe `TRADING_ECONOMICS_API_KEY`.
- Fallback a páginas públicas de Trading Economics.
- Incluye CPI, Core CPI, PPI, Core PPI, NFP y desempleo.
- Nunca inventa consenso.
- Reporta explícitamente qué indicadores no tienen consenso.
- Mantiene el surprise score separado del histórico macro.
- El evento seleccionado es el último publicado disponible por indicador.
- Añade Core PPI al análisis de sorpresa.

## Pesos combinados
- 55% Market Confluence
- 25% Macro Fundamental
- 20% Consensus Surprise

## Ejecución
```bash
python -m pytest -q
python -m gold_scanner.main
```

## Fuentes
- BLS: CPI, Core CPI, PPI, Core PPI, NFP, desempleo.
- Federal Reserve: rango objetivo y calendario FOMC.
- Yahoo / Treasury / FRED / Trading Economics / XAUS: mercado.
- Trading Economics: consenso y datos de calendario.

La reacción posterior al dato intradía sigue reservada para una capa posterior; no se inventa con variaciones diarias.


## V0.5.3
- Normaliza CPI/Core CPI/PPI/Core PPI en métricas MoM y YoY cuando la fuente las distingue.
- Mantiene Actual, Consensus y Previous asociados a la misma métrica y fecha.
- Evita tratar CPI MoM y CPI YoY como duplicados.
- Los eventos publicados y los próximos consensos muestran la métrica normalizada.
