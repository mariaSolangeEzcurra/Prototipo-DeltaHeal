## 🧪 DeltaHeal — reporte de regresión (`full_heal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 38 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 97.4%) |
| Pasan / fallas de aserción / errores | 36 / 2 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 79.0% |
| Iteraciones de self-healing | 1 |
| Tokens (entrada + salida) | 13607 + 5455 = 19062 |
| Costo estimado | $0.0307 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 620.988 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `PUT /pet`
- 🆕 `GET /pet/findByTags`
- 🆕 `DELETE /store/order/{orderId}`
- ✏️ `POST /pet`
- ✏️ `GET /pet/findByStatus`
- ✏️ `GET /pet/{petId}`
- ✏️ `POST /pet/{petId}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_pet_invalid_input`: assert 500 in (400, 422)
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_delete_user_not_found`: assert 200 in (404, 400)
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
