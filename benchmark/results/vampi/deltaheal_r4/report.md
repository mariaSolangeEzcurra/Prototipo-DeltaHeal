## 🧪 DeltaHeal — reporte de regresión (`deltaheal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 60.1% |
| Tests generados | 12 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 7 / 5 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 100.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2102 + 2421 = 4523 |
| Costo estimado | $0.0107 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 681.353 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_delete_users_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_put_user_password_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_post_books_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'
- `test_generated::test_get_book_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'bookTitlec0436bda', 'owner': 'admin', 'secret': 'my_admin_secret'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'arra
- `test_generated::test_get_book_by_title_unauthorized`: jsonschema.exceptions.ValidationError: 'message' is a required property

Failed validating 'required' in schema:
    {'type': 'object',
     'properties': {'status': {'type': 'string', 'enum': ['fail'

