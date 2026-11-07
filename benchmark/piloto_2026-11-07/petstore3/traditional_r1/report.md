## 🧪 DeltaHeal — reporte de regresión (`traditional`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | n/a (sin LLM) |
| Tests generados | 7 |
| Tasa de tests ejecutables | 100.0% |
| Pasan / fallas de aserción / errores | 2 / 5 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 36.8% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 0 + 0 = 0 |
| Costo estimado | $0.0000 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 16.806 s |

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

- `test_schemathesis::test_api[PUT /pet]`: ServerError(operation='PUT /pet', title='Server error', message='', case_id=None, severity=<Severity.CRITICAL: 'critical'>) [single exception in FailureGroup]
- `test_schemathesis::test_api[POST /pet]`: ServerError(operation='POST /pet', title='Server error', message='', case_id=None, severity=<Severity.CRITICAL: 'critical'>) [single exception in FailureGroup]
- `test_schemathesis::test_api[GET /pet/findByTags]`: RejectedPositiveData(operation='GET /pet/findByTags', title='Schema-valid request rejected', message='Valid data should have been accepted\nExpected: 2xx, 3xx, 401, 403, 404, 409, 429, 5xx', case_id=N
- `test_schemathesis::test_api[GET /pet/{petId}]`: IgnoredAuth(operation='GET /pet/{petId}', title='API accepts requests without authentication', message='Expected 401 or 403, got `200 OK` for `GET /pet/{petId}`', case_id='MtkQYx', severity=<Severity.
- `test_schemathesis::test_api[POST /pet/{petId}]`: RejectedPositiveData(operation='POST /pet/{petId}', title='Schema-valid request rejected', message='Valid data should have been accepted\nExpected: 2xx, 3xx, 401, 403, 404, 409, 429, 5xx', case_id=Non

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
- `PUT /pet`: 500
