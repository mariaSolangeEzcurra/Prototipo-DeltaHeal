## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 38 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 35 / 3 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 84.2% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 5920 + 4670 = 10590 |
| Costo estimado | $0.0220 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 57.406 s |

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

- `test_generated::test_delete_store_order_byId_not_found_404`: assert 200 in [400, 404]
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_user_createWithList_success_200`: jsonschema.exceptions.ValidationError: [{'id': 274065, 'username': 'user_5f2072f0', 'firstName': 'Test', 'lastName': 'User', 'email': 'user_5f2072f0@example.com', 'password': 'Password123!', 'phone': 
- `test_generated::test_delete_user_deleteUser_not_found_404`: assert 200 in [400, 404]
 +  where 200 = <Response [200]>.status_code

