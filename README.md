# Gold Scanner V0.6

Scanner macro/market para XAUUSD. No ejecuta operaciones.

## V0.6.1

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


## V0.6.1
- Normaliza CPI/Core CPI/PPI/Core PPI en métricas MoM y YoY cuando la fuente las distingue.
- Mantiene Actual, Consensus y Previous asociados a la misma métrica y fecha.
- Evita tratar CPI MoM y CPI YoY como duplicados.
- Los eventos publicados y los próximos consensos muestran la métrica normalizada.


## V0.6 — Persistent Macro Context
- Mantiene el último dato macro publicado como dato vigente hasta que exista una publicación más reciente.
- Mantiene el último surprise válido (Actual vs Consensus) activo en la ecuación hasta que el mismo indicador/métrica publique un dato nuevo.
- El consenso futuro se muestra como referencia, pero nunca se convierte en surprise antes de la publicación.
- Persiste el estado en `.gold_scanner_state.json`.
- GitHub Actions restaura y guarda ese estado mediante Actions Cache entre ejecuciones.
- Al arrancar desde estado vacío, consulta 180 días de calendario para intentar recuperar el último evento publicado con consenso.
- PPI/CPI futuros continúan mostrando Previous + Consensus mientras el último dato publicado sigue siendo el vigente.


## V0.6.1
- Persistent macro context across GitHub Actions runs.
- BLS CPI/Core CPI/PPI/Core PPI/NFP/Unemployment fetched in one batch request.
- If BLS is temporarily unavailable or quota-limited, the scanner continues using persisted macro context.
- State file is guaranteed to exist before cache save.
- GitHub Actions schedule: every 30 minutes.
