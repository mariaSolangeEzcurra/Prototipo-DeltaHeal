## 🧪 DeltaHeal — reporte de regresión (`traditional`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 2 / 3 / 0 |
| Reducción de contexto enviado al LLM | n/a (sin LLM) |
| Tests generados | 5 |
| Tasa de tests ejecutables | 100.0% |
| Pasan / fallas de aserción / errores | 0 / 5 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 70.0% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 0 + 0 = 0 |
| Costo estimado | $0.0000 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 15.239 s |

<details><summary>Operaciones analizadas</summary>

- 🆕 `PUT /api/v1/items/{id}`
- 🆕 `PATCH /api/v1/users/me/password`
- ✏️ `POST /api/v1/items/`
- ✏️ `DELETE /api/v1/items/{id}`
- ✏️ `GET /api/v1/users/`

</details>

### ⚠️ Posibles regresiones (fallas de aserción)

- `test_schemathesis::test_api[GET /api/v1/users/]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 2 distinct failures
assert not ['FailureGroup: Schemathesis found 2 distinct failures']
- `test_schemathesis::test_api[PATCH /api/v1/users/me/password]`: AssertionError: 2 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
  FailureGroup: Schemathesis found 2 distinct failures
assert not ['FailureGroup: Schemathesis found 1 di
- `test_schemathesis::test_api[POST /api/v1/items/]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[PUT /api/v1/items/{id}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[DELETE /api/v1/items/{id}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']

### Códigos HTTP observados no documentados en el contrato

- `POST /api/v1/items/`: 400
- `DELETE /api/v1/items/{id}`: 404
- `PUT /api/v1/items/{id}`: 404
- `GET /api/v1/users/`: 500
- `PATCH /api/v1/users/me/password`: 400
