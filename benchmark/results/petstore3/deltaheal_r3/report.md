## 🧪 DeltaHeal — reporte de regresión (`deltaheal`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 20 |
| Tasa de tests ejecutables | 100.0% (antes de reparar: 95.0%) |
| Pasan / fallas de aserción / errores | 17 / 3 / 0 |
| Cobertura de respuestas HTTP (ops objetivo) | 79.0% |
| Iteraciones de self-healing | 1 |
| Tokens (entrada + salida) | 6773 + 2922 = 9695 |
| Costo estimado | $0.0160 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 152.843 s |

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

- `test_generated::test_post_pet_invalido_faltan_campos_requeridos`: assert 500 in [400, 422]
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_delete_order_por_id_no_encontrado`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_order_por_id_fuera_de_rango`: assert 200 in [400, 404]
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
