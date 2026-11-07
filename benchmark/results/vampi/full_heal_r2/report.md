## 🧪 DeltaHeal — reporte de regresión (`full_heal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 28 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 20 / 8 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 100.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 4444 + 4483 = 8927 |
| Costo estimado | $0.0201 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 299.37 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_users_v1_login_invalid_credentials_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_me_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string'}

On instance['status']:
    401
- `test_generated::test_delete_users_v1_username_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_users_v1_email_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_users_v1_password_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_post_books_v1_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_get_books_v1_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'book_read_88d768c5', 'owner': 'admin', 'secret': 'readSecret123'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'array
- `test_generated::test_get_books_v1_by_title_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401

