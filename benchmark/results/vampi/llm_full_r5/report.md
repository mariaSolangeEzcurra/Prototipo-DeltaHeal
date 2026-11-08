## 🧪 DeltaHeal — reporte de regresión (`llm_full`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 28 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 18 / 10 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 100.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 4444 + 4551 = 8995 |
| Costo estimado | $0.0204 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 284.185 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_users_v1_register_bad_request_existing_user`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_users_v1_login_invalid_password_returns_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_me_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_delete_users_v1_by_username_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_put_users_v1_email_success`: assert 400 == 204
 +  where 400 = <Response [400]>.status_code
- `test_generated::test_put_users_v1_email_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_put_users_v1_password_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_post_books_v1_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_get_books_v1_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'book_5480763e', 'owner': 'admin', 'secret': 'owner_secret_data'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'array'
- `test_generated::test_get_books_v1_by_title_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'

