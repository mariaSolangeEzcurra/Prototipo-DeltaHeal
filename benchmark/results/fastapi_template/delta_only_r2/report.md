## 🧪 DeltaHeal — reporte de regresión (`delta_only`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 3 / 0 |
| Reducción de contexto enviado al LLM | 67.3% |
| Tests generados | 19 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 19 / 0 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 90.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2560 + 3086 = 5646 |
| Costo estimado | $0.0135 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 568.597 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `PUT /api/v1/items/{id}`
- 🆕 `PATCH /api/v1/users/me/password`
- ✏️ `POST /api/v1/items/`
- ✏️ `DELETE /api/v1/items/{id}`
- ✏️ `GET /api/v1/users/`

</details>

