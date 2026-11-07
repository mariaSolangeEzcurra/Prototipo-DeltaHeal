## 🧪 DeltaHeal — reporte de regresión (`traditional`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | n/a (sin LLM) |
| Tests generados | 7 |
| Tasa de tests ejecutables | 100.0% |
| Pasan / fallas de aserción / errores | 1 / 6 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 73.7% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 0 + 0 = 0 |
| Costo estimado | $0.0000 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 19.451 s |

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

- `test_schemathesis::test_api[PUT /pet]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[POST /pet]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[GET /pet/findByStatus]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[GET /pet/findByTags]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[GET /pet/{petId}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']
- `test_schemathesis::test_api[POST /pet/{petId}]`: AssertionError: 1 violaciones distintas:
  FailureGroup: Schemathesis found 1 distinct failure
assert not ['FailureGroup: Schemathesis found 1 distinct failure']

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
- `PUT /pet`: 500
- `GET /pet/findByTags`: 500
- `POST /pet/{petId}`: 404
