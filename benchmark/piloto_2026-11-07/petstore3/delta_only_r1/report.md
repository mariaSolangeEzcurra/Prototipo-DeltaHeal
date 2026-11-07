## 🧪 DeltaHeal — reporte de regresión (`delta_only`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 32 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 12 / 20 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 52.6% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 6109 = 9028 |
| Costo estimado | $0.0161 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 31.33 s |

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

- `test_generated.TestPetOperations::test_post_pet_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_invalid_input_missing_name`: assert 500 == 400
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_invalid_input_missing_photoUrls`: assert 500 == 400
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_validation_exception_invalid_status`: assert 500 == 422
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_put_pet_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_put_pet_validation_exception_invalid_status`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_put_pet_validation_exception_missing_required_field`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_status_success[available]`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_status_success[pending]`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_status_success[sold]`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_status_multiple_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_tags_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_find_by_tags_multiple_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_get_pet_by_id_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_by_id_update_with_form_success`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_by_id_update_with_form_only_name`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_by_id_update_with_form_only_status`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestPetOperations::test_post_pet_by_id_update_with_form_invalid_input_invalid_status`: assert 500 == 200
 +  where 500 = <Response [500]>.status_code
- `test_generated.TestStoreOrderOperations::test_delete_order_invalid_id_supplied_too_large`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated.TestStoreOrderOperations::test_delete_order_not_found`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
