## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 40 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 38 / 2 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 79.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 5920 + 5127 = 11047 |
| Costo estimado | $0.0237 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 64.869 s |

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
- `test_generated::test_post_user_create_with_list_success`: jsonschema.exceptions.ValidationError: [{'id': 58514, 'username': 'user_rdugqodvze', 'firstName': 'John', 'lastName': 'Doe', 'email': 'jhlqzyff@example.com', 'password': 'secretPassword123', 'phone': 

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
