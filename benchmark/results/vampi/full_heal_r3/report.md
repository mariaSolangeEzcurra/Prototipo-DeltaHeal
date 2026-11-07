## 🧪 DeltaHeal — reporte de regresión (`full_heal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | 0.0% |
| Tests generados | 28 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 100.0%) |
| Pasan / fallas de aserción / errores | 18 / 10 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 100.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 4444 + 4649 = 9093 |
| Costo estimado | $0.0208 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 267.965 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_generated::test_post_users_v1_register_duplicate_fail_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_post_users_v1_login_invalid_password_fail_400`: assert 200 == 400
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_get_me_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string'}

On instance['status']:
    401
- `test_generated::test_delete_user_by_username_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_user_email_success_204`: assert 400 == 204
 +  where 400 = <Response [400]>.status_code
- `test_generated::test_put_user_email_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_put_user_password_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_post_book_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401
- `test_generated::test_get_book_by_title_success`: jsonschema.exceptions.ValidationError: {'book_title': 'bookTitle_1737d8b9', 'owner': 'admin', 'secret': 'secretForTitle'} is not of type 'array'

Failed validating 'type' in schema:
    {'type': 'arra
- `test_generated::test_get_book_by_title_unauthorized_401`: jsonschema.exceptions.ValidationError: 401 is not of type 'string'

Failed validating 'type' in schema['properties']['status']:
    {'type': 'string', 'enum': ['fail']}

On instance['status']:
    401

