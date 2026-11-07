## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 39 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 36 / 3 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 79.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 5920 + 5166 = 11086 |
| Costo estimado | $0.0238 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 160.907 s |

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

- `test_generated::test_post_pet_missing_required_fields_400_or_422`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_post_user_createUsersWithListInput_success_200`: jsonschema.exceptions.ValidationError: [{'id': 878779, 'username': 'user_95f882fe', 'firstName': 'Test', 'lastName': 'User', 'email': '95f882fe@example.com', 'password': 'Password123!', 'phone': '555-
- `test_generated::test_delete_user_deleteUser_not_found_404`: assert 200 in [404, 400]
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
