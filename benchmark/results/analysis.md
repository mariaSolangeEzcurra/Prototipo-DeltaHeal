# Resultados del experimento

Corridas válidas: **75** · APIs: fastapi_template, petstore3, vampi · Configuraciones: A · Tradicional, B · LLM spec completa, C · Prototipo (delta+healing), Abl. delta sin healing, Abl. completa + healing

## Resumen agrupado (media ± desviación estándar)

| Configuración | Tasa de pruebas ejecutables | Cobertura de respuestas HTTP | Tokens totales | Costo (USD) | Duración (s) |
|---|---|---|---|---|---|
| A · Tradicional | 100.0% ± 0.0% | 76.6% ± 9.1% | 0.0 ± 0.0 | 0.0000 ± 0.0000 | 16.2 ± 6.8 |
| B · LLM spec completa | 92.4% ± 25.6% | 82.3% ± 25.1% | 10612.8 ± 1324.1 | 0.0228 ± 0.0023 | 183.9 ± 115.9 |
| C · Prototipo (delta+healing) | 100.0% ± 0.0% | 91.4% ± 8.1% | 5602.3 ± 1788.5 | 0.0119 ± 0.0022 | 225.9 ± 182.9 |
| Abl. delta sin healing | 97.8% ± 3.9% | 88.5% ± 13.1% | 5187.5 ± 632.7 | 0.0119 ± 0.0015 | 192.8 ± 155.7 |
| Abl. completa + healing | 99.3% ± 1.2% | 90.3% ± 9.3% | 12117.1 ± 4098.7 | 0.0249 ± 0.0067 | 239.2 ± 159.9 |

**Reducción de tokens C vs. B:** 47.2% (media 5602 vs. 10613 tokens por corrida).
**Efecto del self-healing en C:** tasa ejecutable 99.3% → 100.0%.

## Pruebas de hipótesis (agrupado)

| Métrica | Kruskal–Wallis H (p) | Par | p (Holm) | δ de Cliff | Efecto |
|---|---|---|---|---|---|
| Tasa de pruebas ejecutables | 11.88 (0.0182) | traditional vs llm_full | 0.0826 | +0.40 | mediano |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | traditional vs deltaheal | 1.0000 | +0.00 | despreciable |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | traditional vs delta_only | 0.3068 | +0.27 | pequeño |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | traditional vs full_heal | 0.3068 | +0.27 | pequeño |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | llm_full vs deltaheal | 0.0826 | -0.40 | mediano |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | llm_full vs delta_only | 1.0000 | -0.06 | despreciable |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | llm_full vs full_heal | 1.0000 | -0.10 | despreciable |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | deltaheal vs delta_only | 0.3068 | +0.27 | pequeño |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | deltaheal vs full_heal | 0.3068 | +0.27 | pequeño |
| Tasa de pruebas ejecutables | 11.88 (0.0182) | delta_only vs full_heal | 1.0000 | -0.07 | despreciable |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | traditional vs llm_full | 0.2705 | -0.44 | mediano |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | traditional vs deltaheal | 0.0070 | -0.72 | grande |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | traditional vs delta_only | 0.1559 | -0.50 | grande |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | traditional vs full_heal | 0.0150 | -0.67 | grande |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | llm_full vs deltaheal | 1.0000 | -0.21 | pequeño |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | llm_full vs delta_only | 1.0000 | -0.10 | despreciable |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | llm_full vs full_heal | 1.0000 | -0.15 | despreciable |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | deltaheal vs delta_only | 1.0000 | +0.07 | despreciable |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | deltaheal vs full_heal | 1.0000 | +0.07 | despreciable |
| Cobertura de respuestas HTTP | 13.90 (0.0076) | delta_only vs full_heal | 1.0000 | -0.07 | despreciable |
| Tokens totales | 62.31 (0.0000) | traditional vs llm_full | 0.0000 | -1.00 | grande |
| Tokens totales | 62.31 (0.0000) | traditional vs deltaheal | 0.0000 | -1.00 | grande |
| Tokens totales | 62.31 (0.0000) | traditional vs delta_only | 0.0000 | -1.00 | grande |
| Tokens totales | 62.31 (0.0000) | traditional vs full_heal | 0.0000 | -1.00 | grande |
| Tokens totales | 62.31 (0.0000) | llm_full vs deltaheal | 0.0001 | +0.91 | grande |
| Tokens totales | 62.31 (0.0000) | llm_full vs delta_only | 0.0000 | +1.00 | grande |
| Tokens totales | 62.31 (0.0000) | llm_full vs full_heal | 0.9615 | -0.16 | pequeño |
| Tokens totales | 62.31 (0.0000) | deltaheal vs delta_only | 0.9615 | -0.08 | despreciable |
| Tokens totales | 62.31 (0.0000) | deltaheal vs full_heal | 0.0001 | -0.93 | grande |
| Tokens totales | 62.31 (0.0000) | delta_only vs full_heal | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | traditional vs llm_full | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | traditional vs deltaheal | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | traditional vs delta_only | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | traditional vs full_heal | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | llm_full vs deltaheal | 0.0000 | +1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | llm_full vs delta_only | 0.0000 | +1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | llm_full vs full_heal | 0.9106 | -0.16 | pequeño |
| Costo (USD) | 64.58 (0.0000) | deltaheal vs delta_only | 0.9106 | -0.08 | despreciable |
| Costo (USD) | 64.58 (0.0000) | deltaheal vs full_heal | 0.0000 | -1.00 | grande |
| Costo (USD) | 64.58 (0.0000) | delta_only vs full_heal | 0.0000 | -1.00 | grande |
| Duración (s) | 36.21 (0.0000) | traditional vs llm_full | 0.0000 | -0.99 | grande |
| Duración (s) | 36.21 (0.0000) | traditional vs deltaheal | 0.0000 | -1.00 | grande |
| Duración (s) | 36.21 (0.0000) | traditional vs delta_only | 0.0000 | -0.99 | grande |
| Duración (s) | 36.21 (0.0000) | traditional vs full_heal | 0.0000 | -0.99 | grande |
| Duración (s) | 36.21 (0.0000) | llm_full vs deltaheal | 1.0000 | -0.09 | despreciable |
| Duración (s) | 36.21 (0.0000) | llm_full vs delta_only | 1.0000 | +0.13 | despreciable |
| Duración (s) | 36.21 (0.0000) | llm_full vs full_heal | 1.0000 | -0.23 | pequeño |
| Duración (s) | 36.21 (0.0000) | deltaheal vs delta_only | 1.0000 | +0.10 | despreciable |
| Duración (s) | 36.21 (0.0000) | deltaheal vs full_heal | 1.0000 | -0.11 | despreciable |
| Duración (s) | 36.21 (0.0000) | delta_only vs full_heal | 1.0000 | -0.26 | pequeño |

## Friedman (bloques = API × repetición)

- Tasa de pruebas ejecutables: χ² = 11.10, p = 0.0255
- Cobertura de respuestas HTTP: χ² = 34.89, p = 0.0000
- Tokens totales: χ² = 54.13, p = 0.0000
- Costo (USD): χ² = 54.13, p = 0.0000
- Duración (s): χ² = 31.52, p = 0.0000

Detalle por API en `tests.csv` y `summary_by_api.csv`.

_Nota: con n = 5 por celda la potencia estadística es limitada; reporta tamaños de efecto junto con los p-valores y evita concluir equivalencia a partir de p > 0.05._
