## 🧪 DeltaHeal — reporte de regresión (`delta_only`)

| Métrica | Valor |
|---|---|
| Operaciones nuevas / modificadas / eliminadas | 3 / 4 / 0 |
| Reducción de contexto enviado al LLM | 55.6% |
| Tests generados | 20 |
| Tasa de tests ejecutables | 95.0% (antes de reparar: 95.0%) |
| Pasan / fallas de aserción / errores | 15 / 4 / 1 |
| Cobertura de respuestas HTTP (ops objetivo) | 68.4% |
| Iteraciones de self-healing | 0 |
| Tokens (entrada + salida) | 2919 + 3486 = 6405 |
| Costo estimado | $0.0153 |
| Respuestas del LLM cortadas por límite de salida | 0 |
| Duración total | 208.618 s |

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

- `test_generated::test_post_pet_faltan_campos_requeridos_error`: assert 200 in (400, 422)
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_put_pet_cuerpo_invalido_422_o_400`: assert 500 in (400, 422)
 +  where 500 = <Response [500]>.status_code
- `test_generated::test_delete_order_no_encontrada_404`: assert 200 == 404
 +  where 200 = <Response [200]>.status_code
- `test_generated::test_delete_order_id_fuera_de_rango_400_o_404`: assert 200 in (400, 404)
 +  where 200 = <Response [200]>.status_code

### Códigos HTTP observados no documentados en el contrato

- `PUT /pet`: 500
