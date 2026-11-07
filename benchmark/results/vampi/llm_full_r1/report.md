## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 28 |
| Tasa de tests ejecutables | 0.0% (antes de reparar: 0.0%) |
| Pasan / fallas de aserción / errores | 0 / 0 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 0.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 4444 + 4351 = 8795 |
| Costo estimado | $0.0196 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 88.808 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

> ❌ El archivo de pruebas final no se pudo colectar en Pytest (ver artefactos `junit_*.xml`).

