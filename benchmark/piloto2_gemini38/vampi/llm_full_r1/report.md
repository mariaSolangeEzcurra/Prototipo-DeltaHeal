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
| Tokens (entrada + salida) | 4444 + 4447 = 8891 |
| Costo estimado | $0.0200 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 49.96 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_users_register_existing_user_bad_request`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_users_login_invalid_password`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_me_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string'}

On instance['status']:
    401
- `test_generated::test_delete_user_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_user_email_success`: assert 400 == 204
 +  where 400 = <Response [400]>.status_code
- `test_generated::test_put_user_email_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_user_password_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_post_books_v1_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_get_book_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'book_get_b58cf4ae', 'owner': 'admin', 'secret': 'admin_owned_secret'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'a
- `test_generated::test_get_book_by_title_unauthorized`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401

