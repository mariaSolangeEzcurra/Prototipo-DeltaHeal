## 🧪 DeltaHeal — reporte de regresión (`delta_only`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 21 |
| Tasa de tests ejecutables | 90.5% (antes de reparar: 90.5%) |
| Pasan / fallas de aserción / errores | 16 / 3 / 2 |
| Cobertura de respuestas HTTP (ops objetivo) | 73.7% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 2596 = 5515 |
| Costo estimado | $0.0119 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 87.923 s |

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

- `test_generated::test_post_pet_invalid_input_missing_required_fields`: assert 500 in (400, 422)
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_put_pet_validation_exception_missing_required`: assert 404 in (400, 422)
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_order_invalid_id_above_limit`: assert 200 in (400, 404)
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
