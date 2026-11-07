## 🧪 DeltaHeal — reporte de regresión (`full_heal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 28 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 17 / 11 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 100.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 4444 + 4733 = 9177 |
| Costo estimado | $0.0211 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 99.877 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_users_v1_register_duplicate_username_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_users_v1_login_invalid_password_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_me_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string'},
              
- `test_generated::test_delete_user_by_username_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_put_user_email_success_204`: assert 400 == 204
 +  where 400 = <Response [400]>.status_code
- `test_generated::test_put_user_email_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_put_user_password_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_post_books_v1_duplicate_400`: jsonschema.exceptions.ValidationError: 'status' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail']
- `test_generated::test_post_books_v1_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_get_book_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'book_admin_d7fabaa3', 'owner': 'admin', 'secret': 'adminSecret'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'array'
- `test_generated::test_get_book_by_title_unauthorized_401`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'

