## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 3 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 43 |
| Tasa de tests ejecutables | 97.7% (antes de reparar: 97.7%) |
| Pasan / fallas de aserción / errores | 40 / 2 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 90.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 6664 + 5250 = 11914 |
| Costo estimado | $0.0247 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 299.166 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `PUT /api/v1/items/{id}`
- 🆕 `PATCH /api/v1/users/me/password`
- ✏️ `POST /api/v1/items/`
- ✏️ `DELETE /api/v1/items/{id}`
- ✏️ `GET /api/v1/users/`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_password_recovery_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_utils_test_email_success`: assert 500 == 201
 +  where 500 = <Response [500]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `GET /api/v1/users/`: 401
