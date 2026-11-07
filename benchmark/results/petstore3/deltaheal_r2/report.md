## 🧪 DeltaHeal — reporte de regresión (`deltaheal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 21 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 18 / 3 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 84.2% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 2553 = 5472 |
| Costo estimado | $0.0118 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 334.958 s |

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

- `test_generated::test_post_pet_missing_required_fields`: assert 500 in (400, 422)
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_put_pet_missing_required_fields`: assert 404 in (400, 422)
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_order_not_found_or_above_limit`: assert 200 in (404, 400)
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
