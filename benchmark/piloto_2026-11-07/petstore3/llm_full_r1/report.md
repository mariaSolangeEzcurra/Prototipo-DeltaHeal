## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 46 |
| Tasa de tests ejecutables | 95.7% (antes de reparar: 95.7%) |
| Pasan / fallas de aserción / errores | 29 / 15 / 2 |
| Cobertura de respuestas HTTP (ops objetivo) | 73.7% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 5920 + 8723 = 14643 |
| Costo estimado | $0.0236 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 43.936 s |

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

- `test_generated::test_post_pet_invalid_input_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_pet_validation_exception_422`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_put_pet_validation_exception_422`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_pet_findByStatus_success`: Failed: Schema validation failed: 'name' is a required property in deque([])
- `test_generated::test_get_pet_findByTags_success`: assert False
 +  where False = any(<generator object test_get_pet_findByTags_success.<locals>.<genexpr> at 0x00000237FABEB760>)
- `test_generated::test_post_pet_byId_updateWithForm_invalid_input_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_pet_not_found_404`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_pet_byId_uploadImage_no_file_400`: assert 500 == 400
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_store_order_validation_exception_422`: assert 200 == 422
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_store_order_not_found_404`: assert 200 in [400, 404]
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_user_createWithList_success`: Failed: Schema validation failed: [{'id': 199146, 'username': 'user_zacro', 'firstName': 'John_lsg', 'lastName': 'Doe_tym', 'email': 'user_zacro@example.com', 'password': 'password123', 'phone': '123-
- `test_generated::test_get_user_login_invalid_credentials_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_user_byName_invalid_username_400`: assert 404 == 400
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_user_invalid_username_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_user_not_found_404`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code

