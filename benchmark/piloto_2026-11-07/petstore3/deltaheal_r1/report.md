## 🧪 DeltaHeal — reporte de regresión (`deltaheal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 26 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 8 / 18 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 42.1% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 5369 = 8288 |
| Costo estimado | $0.0143 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 28.231 s |

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

- `test_generated::test_post_pet_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_invalid_input_missing_name`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_invalid_input_missing_photoUrls`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_invalid_status_value`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_put_pet_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_put_pet_invalid_id_supplied`: assert 404 == 400
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_put_pet_validation_exception_invalid_status`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_findByStatus_success_available`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_findByStatus_success_multiple_status`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_findByStatus_no_status_param`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_findByTags_success_single_tag`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_findByTags_success_multiple_tags`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_get_pet_by_id_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_id_update_with_form_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_id_update_with_form_only_name`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_pet_id_update_with_form_invalid_id`: assert 404 == 400
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_post_pet_id_update_with_form_invalid_status_value`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_delete_order_not_found`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
- `POST /pet/{petId}`: 404
