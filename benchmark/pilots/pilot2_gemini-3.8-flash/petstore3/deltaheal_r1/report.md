## 🧪 DeltaHeal — reporte de regresión (`deltaheal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 20 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 18 / 2 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 84.2% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 2595 = 5514 |
| Costo estimado | $0.0119 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 67.264 s |

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

- `test_generated::test_post_pet_missing_required_fields`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_delete_order_out_of_range_or_not_found`: assert 200 in [400, 404]
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
