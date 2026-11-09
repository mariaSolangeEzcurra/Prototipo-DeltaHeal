# Evaluación experimental (benchmark)

Comparación controlada de DeltaHeal con otras estrategias de generación de pruebas, sobre APIs de
referencia y en condiciones idénticas. La demostración de la herramienta no requiere este entorno:
ver el [README principal](../README.md#demostración).

## Contenido
1. [Configuraciones comparadas](#1-configuraciones-comparadas)
2. [APIs evaluadas](#2-apis-evaluadas)
3. [Protocolo de cada ejecución](#3-protocolo-de-cada-ejecución)
4. [Ejecución](#4-ejecución)
5. [Resultados](#5-resultados)
6. [Evidencia en Excel](#6-evidencia-en-excel)
7. [Métricas](#7-métricas)
8. [Ejecuciones piloto](#8-ejecuciones-piloto)
9. [Solución de problemas](#solución-de-problemas)

---

## 1. Configuraciones comparadas

[config.yaml](config.yaml) define **5 configuraciones × 3 APIs × 5 repeticiones = 75 ejecuciones**.

| Config. | `--mode` | Análisis delta | Auto-corrección | Descripción |
|---|---|---|---|---|
| **A** | `traditional` | — | — | Herramienta sin IA: Schemathesis genera casos a partir del contrato, con datos válidos e inválidos |
| **B** | `llm_full` | ✗ | ✗ | IA básica: se envía el contrato completo y el código se ejecuta sin modificaciones |
| **C** | `deltaheal` | ✓ | ✓ | DeltaHeal |
| Control | `delta_only` | ✓ | ✗ | aísla el aporte del análisis delta |
| Control | `full_heal` | ✗ | ✓ | aísla el aporte de la auto-corrección |

**Automatización de las configuraciones A y B.**
- **A** representa una herramienta automática de uso habitual en CI, no pruebas manuales; se
  ejecuta como lo haría un equipo de desarrollo.
- **B** reproduce el uso directo de un LLM: enviar el contrato completo, solicitar las pruebas y
  ejecutarlas sin corrección. Usa **el mismo prompt** que C y solo difiere en el contexto enviado,
  de modo que la comparación aísla el efecto del análisis delta y de la auto-corrección,
  independientemente de la redacción del prompt.
- La automatización garantiza **reproducibilidad** (5 repeticiones en condiciones idénticas) y
  **medición exacta** de tokens y tiempos.
- Para contrastar con pruebas realizadas por personas (Postman o un chat de IA), se dispone de la
  hoja **Registro_manual** del Excel y de la sección **Revisión manual** del [visor](viewer/).

## 2. APIs evaluadas

| API | Complejidad | Operaciones | Autenticación | Cambio simulado (operaciones objetivo) | Reducción del contexto enviado |
|---|---|---|---|---|---|
| **Swagger Petstore v3** | baja | 19 | no | 3 endpoints nuevos + campo `tags` en `Pet` (7 ops) | 56 % |
| **VAmPI** | media | 14 | JWT (`admin`) | 2 endpoints nuevos + 2 respuestas 401 documentadas (4 ops) | 60 % |
| **Full Stack FastAPI Template** | alta (FastAPI + PostgreSQL) | 23 | JWT (superusuario) | 2 endpoints nuevos, 1 campo, 1 parámetro y 1 respuesta (5 ops) | 67 % |

- **Petstore** es una API de referencia utilizada en diversos estudios sobre testing de APIs.
- **VAmPI** es una API vulnerable por diseño; se ejecuta en modo seguro (`vulnerable=0`).
- **FastAPI Template** incluye base de datos, validaciones y roles; la base de datos se recrea en
  cada ejecución.

Las versiones están **fijadas por commit** ([setup_apis.py](setup_apis.py)) y sus contratos
([specs/](specs/)) se extrajeron de esos mismos commits.

## 3. Protocolo de cada ejecución

**Escenario de cambio.** Dado que las APIs de referencia no incluyen un historial de cambios del
contrato, la versión *nueva* corresponde a la API en ejecución y la versión *base* se obtiene
retirando elementos según la sección `scenario` de cada API en [config.yaml](config.yaml):
`remove_operations` (endpoints nuevos), `remove_properties` (campos nuevos), `remove_required`
(campos que pasaron a ser obligatorios), `remove_parameters` (parámetros nuevos) y
`remove_responses` (respuestas documentadas). Así, todo cambio detectado existe en la aplicación.

**Estado inicial verificado.** Antes de cada ejecución la API se recrea con Docker (contenedor o
base de datos nueva, entre 4 y 17 segundos), se cargan los datos iniciales (`setup`) y se ejecuta
una **prueba de humo** (`smoke`). Si falla, se reintenta; si persiste, la ejecución se omite sin
consumir cuota.

**Autenticación.** Antes de cada ejecución se inicia sesión (`auth`) y el mismo token se usa en A,
B y C: las pruebas generadas lo reciben en la fixture `api` y Schemathesis como header. Los prompts
de B y C incluyen la misma descripción del entorno (`context_note`).

**Orden aleatorio.** El orden de las configuraciones se aleatoriza dentro de cada repetición con
semilla fija, para evitar efectos de orden (calentamiento de la API, caché del proveedor).

## 4. Ejecución

Requisitos: Docker en ejecución y una clave de Gemini en `.env` (ver el README principal).

```powershell
# preparación (una vez): descarga el código fijado y construye las imágenes
python benchmark/setup_apis.py

# ejecución corta: 1 repetición, solo Petstore
python benchmark/run.py --apis petstore3 --reps 1

# experimento completo (reanudable ante interrupciones o cuota agotada)
python benchmark/run.py

# análisis estadístico, gráficos y Excel
python benchmark/analyze.py benchmark/results/results.csv
python benchmark/export_excel.py
```

**Configuración de prueba sin costo** (API de ejemplo e IA simulada, sin Docker):
```powershell
uvicorn demo_api.app:app --port 8000      # en otra terminal
python benchmark/run.py -c benchmark/config.demo.yaml
```

> [results/](results/) contiene las 75 ejecuciones completas, por lo que `run.py` con la
> configuración por defecto no ejecuta nada nuevo. Para un nuevo experimento (otro modelo u otros
> parámetros), definir otra carpeta en `output_dir`: todas las ejecuciones de un experimento deben
> realizarse en las mismas condiciones.

**Tiempos.** Cada ejecución con IA toma en promedio entre 2 y 6 minutos, casi en su totalidad por
la latencia del nivel gratuito de Gemini. La recreación de la API toma segundos y la ejecución de
las pruebas, entre 5 y 9 segundos.

## 5. Resultados

Reporte completo en [results/analysis.md](results/analysis.md). Promedios de las 3 APIs:

| Configuración | Pruebas ejecutables | Cobertura HTTP | Tokens | Costo equiv. (USD) | Duración (s) |
|---|---|---|---|---|---|
| A · Herramienta sin IA | 100.0 % | 76.6 % | 0 | 0.0000 | 16 |
| B · IA con contrato completo | 92.4 % | 82.3 % | 10 613 | 0.0228 | 184 |
| **C · DeltaHeal** | **100.0 %** | **91.4 %** | **5 602** | **0.0119** | 226 |
| Control: delta sin auto-corrección | 97.8 % | 88.5 % | 5 188 | 0.0119 | 193 |
| Control: contrato completo con auto-corrección | 99.3 % | 90.3 % | 12 117 | 0.0249 | 239 |

Interpretación:
- **Tokens y costo:** C consume 47 % menos tokens que B; la diferencia es estadísticamente
  significativa.
- **Cobertura:** C supera a la herramienta sin IA (91.4 % frente a 76.6 %); la diferencia es
  estadísticamente significativa.
- **Pruebas ejecutables:** C alcanza 100 % y B 92.4 %; con 5 repeticiones por caso, la diferencia
  no alcanza significancia estadística.
- **Duración:** no es comparable entre configuraciones, porque la latencia medida de cada llamada
  incluye las esperas y reintentos del nivel gratuito del proveedor.

Métodos estadísticos: Kruskal–Wallis entre configuraciones, Mann–Whitney U por pares con
corrección de Holm, δ de Cliff como tamaño del efecto y Friedman con bloques API × repetición.

| Archivo en `results/` | Contenido |
|---|---|
| `results.csv` | una fila por ejecución |
| `analysis.md` | tablas y pruebas estadísticas |
| `summary_*.csv`, `tests.csv` | resúmenes y comparaciones por métrica |
| `fig_*.png` | diagramas de caja por métrica |
| `evidencia_*.xlsx` | evidencia completa ([sección 6](#6-evidencia-en-excel)) |
| `condiciones_experimento.json` | modelo, parámetros, versiones de software y commits de las APIs |
| `<api>/<config>_r<rep>/` | archivos de cada ejecución |
| `<api>/scenario/` | contrato base (`base.yaml`) y nuevo (`head.yaml`) de cada API |

> Las ejecuciones registradas usan la nomenclatura anterior para los resultados de Pytest
> (`junit_test_generated_<marca de tiempo>.xml`); las nuevas usan `junit_iterN.xml`.

## 6. Evidencia en Excel

Se genera al finalizar (o interrumpirse) el experimento: un libro **general**
(`evidencia_experimento.xlsx`) y **uno por API** (`evidencia_<api>.xlsx`). Generación manual:
`python benchmark/export_excel.py`. El [visor](viewer/) presenta las mismas hojas en el navegador.

| Hoja | Contenido |
|---|---|
| **Leeme** | descripción, modelo utilizado y origen de cada dato |
| **Resumen** | promedios por configuración y reducción de tokens C vs. B |
| **Condiciones** | modelo y parámetros, versiones de software, commits de las APIs y escenarios de cambio |
| **Corridas** | una fila por ejecución: fecha, API, configuración, pruebas, cobertura, tokens, costo, iteraciones |
| **Pasos** | bitácora con la hora de cada etapa de cada ejecución |
| **Codigo_generado** | archivo de pruebas final de cada ejecución |
| **Trafico_HTTP** | cada petición HTTP enviada a la API, con la prueba de origen y el código de respuesta |
| **Llamadas_LLM** | cada llamada al modelo: fase (generación/reparación), tokens, latencia, truncamiento |
| **Prompts** | texto exacto de cada prompt enviado y de cada respuesta recibida |
| **Casos_de_prueba** | resultado final de cada prueba generada |
| **Cobertura** | por operación: códigos HTTP documentados, observados y cubiertos |
| **Registro_manual** | plantilla opcional para pruebas realizadas por personas |

## 7. Métricas

| Métrica | Definición |
|---|---|
| **Tasa de pruebas ejecutables** | pruebas que se ejecutan hasta el final (aprobadas o con falla de aserción) / pruebas generadas. Errores de sintaxis, `NameError`, fixtures inexistentes, etc. se consideran no ejecutables. |
| **Cobertura de respuestas HTTP** | pares (operación, código HTTP) documentados en el contrato **y** observados en el tráfico / pares documentados. Se calcula sobre las operaciones modificadas, con el mismo denominador para todas las configuraciones. |
| **Tokens** | entrada + salida reportados por el proveedor (incluye tokens de razonamiento), separados en generación y reparación. |
| **Costo equivalente** | tokens × precio de lista de la capa de pago. En el nivel gratuito el costo real es 0. |

## 8. Ejecuciones piloto

Ejecuciones previas al experimento final, en [pilots/](pilots/):

| Carpeta | Descripción |
|---|---|
| `pilot1_gemini-2.5-flash/` | 1 repetición sobre Petstore con `gemini-2.5-flash` (7-nov-2026) |
| `pilot2_gemini-3.8-flash/` | 1 repetición sobre las 3 APIs con `gemini-3.8-flash`, el modelo del experimento final (7-nov-2026) |

## Solución de problemas

| Mensaje | Solución |
|---|---|
| `esperando que la API responda…` sin avanzar | Docker no está en ejecución. |
| `falta benchmark/apis/...` | Ejecutar una vez `python benchmark/setup_apis.py`. |
| `container name ... already in use` | Se resuelve automáticamente; si persiste: `docker rm -f petstore3` (o `vampi`). |
| `port is already allocated` | Otro proceso usa el puerto 8080 (Petstore), 5000 (VAmPI) u 8000 (FastAPI). |
| `no se pudo iniciar sesión` | La API no terminó de iniciar; ejecutar nuevamente (la ejecución queda pendiente). |
| `Se agotó la cuota diaria` | Ejecutar nuevamente al día siguiente; el experimento continúa donde quedó. |
| "Respuestas cortadas" > 0 en el reporte | El modelo agotó el límite de salida; aumentar `max_tokens` en `config.yaml`. |
