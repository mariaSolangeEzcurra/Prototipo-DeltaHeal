## 🧪 DeltaHeal — reporte de regresión (`full_heal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 48 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 97.9%) |
| Pasan / fallas de aserción / errores | 33 / 15 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 79.0% |
| Iteraciones de self-healing | 2 |
| Tokens (entrada + salida) | 22562 + 13145 = 35707 |
| Costo estimado | $0.0396 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 68.467 s |

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

- `test_generated::test_post_pet_add_new_pet_400_invalid_input`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_pet_add_new_pet_422_validation_exception`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_put_pet_update_existing_pet_422_validation_exception`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_pet_find_by_status_200_pending_and_sold`: assert 400 == 200
 +  where 400 = <Response [400]>.status_code
- `test_generated::test_post_pet_update_with_form_200`: Failed: Schema validation failed: Additional properties are not allowed ('category', 'id', 'name', 'photoUrls', 'status', 'tags' were unexpected) for data: {'id': 832287, 'category': {'id': 320161, 'n
- `test_generated::test_post_pet_upload_image_200`: Failed: Schema validation failed: Additional properties are not allowed ('category', 'id', 'name', 'photoUrls', 'status', 'tags' were unexpected) for data: {'id': 330298, 'category': {'id': 427423, 'n
- `test_generated::test_post_pet_upload_image_400_no_file_uploaded`: assert 500 == 400
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_store_order_422_validation_exception`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_store_order_404_order_not_found`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_user_create_with_list_200`: Failed: Schema validation failed: [{'id': 328248, 'username': 'user-pnlyu', 'firstName': 'John-obi', 'lastName': 'Doe-nxl', 'email': 'john.doe.qsn@example.com', 'password': 'password123', 'phone': '12
- `test_generated::test_post_user_create_with_list_default_error`: assert 200 >= 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_user_login_400_invalid_credentials`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_user_by_name_400_invalid_username_supplied`: assert 404 == 400
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_user_400_invalid_username_supplied`: assert 404 == 400
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_user_404_user_not_found`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code

