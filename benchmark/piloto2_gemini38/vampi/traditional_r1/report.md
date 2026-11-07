## 🧪 DeltaHeal — reporte de regresión (`traditional`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 2 / 0 |
| Reducción de contexto enviado al LLM | n/a (sin LLM) |
| Tests generados | 4 |
| Tasa de tests ejecutables | 100.0% |
| Pasan / fallas de aserción / errores | 0 / 4 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 91.7% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 0 + 0 = 0 |
| Costo estimado | $0.0000 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 33.104 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `POST /books/v1`
- 🆕 `PUT /users/v1/{username}/password`
- ✏️ `GET /books/v1/{book_title}`
- ✏️ `DELETE /users/v1/{username}`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_schemathesis::test_api[DELETE /users/v1/{username}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[PUT /users/v1/{username}/password]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[POST /books/v1]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[GET /books/v1/{book_title}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']

