## 🧪 DeltaHeal — reporte de regresión (`delta_only`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 21 |
| Tasa de tests ejecutables | 90.5% (antes de reparar: 90.5%) |
| Pasan / fallas de aserción / errores | 16 / 3 / 2 |
| Cobertura de respuestas HTTP (ops objetivo) | 68.4% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 3282 = 6201 |
| Costo estimado | $0.0145 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 27.265 s |

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

- `test_generated::test_post_pet_sin_campos_requeridos_error_400_o_422`: assert 500 in (400, 422)
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_put_pet_cuerpo_invalido_error_400_o_422`: assert 404 in (400, 422)
 +  where 404 = <Response [404]>.status_code
- `test_generated::test_delete_store_order_fuera_de_rango_400`: assert 200 in (400, 404)
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `POST /pet`: 500
