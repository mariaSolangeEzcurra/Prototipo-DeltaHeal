# DeltaHeal — testing de regresión de APIs REST con LLMs en CI/CD

Prototipo orquestador en Python, integrado en GitHub Actions, que **genera y ejecuta pruebas de
regresión de APIs REST usando un LLM**. Ataca los dos problemas de los enfoques actuales:

| Problema | Cómo lo resuelve DeltaHeal |
|---|---|
| **Alto consumo de tokens**: se envía la especificación OpenAPI completa en cada ejecución | **Análisis delta**: con `git diff` detecta qué endpoints cambiaron y envía al LLM solo esos (con los esquemas que usan). Si el contrato no cambió, no llama al LLM (**0 tokens**). |
| **Alucinaciones sintácticas**: el código generado no compila o no se ejecuta | **Bucle de auto-corrección (self-healing)**: ejecuta Pytest, captura los errores y le pide al LLM que repare **solo los tests que fallaron**, hasta 3 veces. |

Además incluye el **experimento controlado** de la tesis: compara la herramienta tradicional, el
LLM básico y el prototipo sobre varias APIs con repeticiones. Exporta toda la **evidencia a Excel**:
prompts exactos, respuestas, tokens, resultados de cada test y cobertura.

---

## Índice
1. [Cómo funciona](#1-cómo-funciona)
2. [Requisitos](#2-requisitos)
3. [Instalación (Windows)](#3-instalación-windows)
4. [Configurar el LLM gratuito (Gemini)](#4-configurar-el-llm-gratuito-gemini)
5. [Primera prueba (API demo)](#5-primera-prueba-con-la-api-demo)
6. [El experimento](#6-el-experimento)
7. [Evidencia en Excel](#7-evidencia-en-excel)
8. [Integración con GitHub Actions](#8-integración-con-github-actions)
9. [Configuraciones del experimento y por qué son automáticas](#9-configuraciones-del-experimento-y-por-qué-son-automáticas)
10. [Métricas](#10-métricas-definición-operativa)
11. [Estructura del proyecto](#11-estructura-del-proyecto)
12. [Solución de problemas](#12-solución-de-problemas)

---

## 1. Cómo funciona

```
 Pull Request que modifica openapi.yaml
                │
                ▼
 ① git diff sobre la especificación ──► ¿cambió? ──no──► fin (0 tokens)
                │ sí
                ▼
 ② Análisis delta: compara cada operación (método + ruta) entre la versión base y la nueva,
    resolviendo los $ref. Un cambio en un esquema marca todos los endpoints que lo usan.
                │
                ▼
 ③ Sub-especificación mínima: solo endpoints nuevos/modificados + esquemas que necesitan
                │
                ▼
 ④ El LLM genera un archivo Pytest            ◄─────────────────────────────┐
                │                                                            │
                ▼                                                            │
 ⑤ Se ejecuta Pytest contra la API real, registrando cada petición HTTP       │
                │                                                            │
                ▼                                                            │
 ⑥ ¿Hay errores en el CÓDIGO de prueba? (sintaxis, NameError, imports…)        │
        │ sí (y quedan iteraciones)                    │ no                  │
        └──► se envían solo los tests rotos + errores ─┘──────────────────────┘
                                                       ▼
 ⑦ Reporte: tests ejecutables, cobertura HTTP, tokens, costo y POSIBLES REGRESIONES
    (fallas de aserción: la API respondió distinto a lo que dice su contrato)
```

**Principio clave:** el bucle repara errores del **código de prueba**, nunca las fallas de
aserción. Si un test falla porque la API respondió 500 en vez de 200, eso puede ser una
regresión real, y "repararla" la ocultaría. Por eso se reporta y no se toca.

**Ejemplo concreto (API demo):** el commit agrega `PATCH /pets/{petId}` y el campo `age` al
esquema de mascota. El análisis delta detecta 1 operación nueva y 3 modificadas (las que usan ese
esquema), y **excluye** `DELETE /pets/{petId}` porque no cambió.

---

## 2. Requisitos

| Programa | Para qué | Dónde |
|---|---|---|
| Python 3.10 o superior | ejecutar el prototipo | python.org (marca **"Add Python to PATH"**) |
| Git | análisis delta y GitHub | git-scm.com |
| Docker Desktop | levantar las APIs del experimento | docker.com |
| Cuenta de Google | clave gratuita de Gemini | aistudio.google.com |
| Cuenta de GitHub | integración CI/CD | github.com |

---

## 3. Instalación (Windows)

Abre PowerShell en la carpeta del proyecto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest
```
Debe terminar con **`32 passed`**.

> **Cada vez** que abras una terminal nueva, activa el entorno (`.venv\Scripts\Activate.ps1`).
> Sabrás que está activo porque la línea empieza con `(.venv)`.
> Mac/Linux: `source .venv/bin/activate`.

---

## 4. Configurar el LLM gratuito (Gemini)

1. Entra a **https://aistudio.google.com/apikey** y pulsa **Create API key**. Copia la clave.
2. Crea el archivo `.env` a partir del ejemplo y pega tu clave:
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   ```
   GEMINI_API_KEY=tu-clave
   ```
   El archivo `.env` **nunca se sube a GitHub** (está en `.gitignore`).
3. Verifica:
   ```powershell
   python -m deltaheal check-llm
   ```
   Debe terminar con **✅ Conexión correcta**.

**Límites del nivel gratuito:** Google limita las llamadas por minuto y por día, y cada modelo
tiene su propia cuota. Puedes ver tus límites en https://ai.dev/rate-limit. El prototipo espacia las
llamadas automáticamente. Si se agota la cuota del día, se detiene sin perder nada, y al
ejecutarlo de nuevo continúa donde quedó. La cuota se reinicia a medianoche hora del Pacífico
(3:00 a.m. en Lima).

Otros proveedores soportados: `--provider groq` (gratis, clave `GROQ_API_KEY`),
`--provider ollama` (modelo local, sin límites), y `deepseek`/`openai` (de pago).
Lista de modelos disponibles para tu clave: `python -m deltaheal models`.

---

## 5. Primera prueba con la API demo

Necesitas **dos terminales** con el entorno activado.

**Terminal 1**: levanta la API demo y déjala abierta.
```powershell
uvicorn examples.demo_api.app:app --port 8000
```
Comprueba en el navegador que `http://127.0.0.1:8000/pets` muestra `[]`.

**Terminal 2**, sin gastar cuota (LLM simulado):
```powershell
python -m deltaheal run --mode deltaheal --provider mock --model mock-1 --spec examples/demo_api/openapi_v2.yaml --old-spec examples/demo_api/openapi_v1.yaml --base-url http://127.0.0.1:8000
```
El LLM simulado mete un error a propósito: verás *tasa ejecutable 75 % → 100 %* tras 1 reparación.

**Terminal 2**, con Gemini:
```powershell
python -m deltaheal run --mode deltaheal --spec examples/demo_api/openapi_v2.yaml --old-spec examples/demo_api/openapi_v1.yaml --base-url http://127.0.0.1:8000
```

Dónde queda todo (`deltaheal-out\deltaheal\`):

| Archivo | Contenido |
|---|---|
| `report.md` / `report.json` | reporte legible / métricas completas |
| `test_generated.py` | pruebas finales; `test_generated.iterN.py` = cada versión del bucle |
| `llm_calls\NN_fase_prompt.txt` | prompt **exacto** enviado al LLM |
| `llm_calls\NN_fase_response.txt` | respuesta **exacta** del LLM |
| `junit_*.xml` | resultado de Pytest por iteración |
| `http_final.jsonl` | cada petición HTTP hecha a la API y su código de respuesta |
| `spec_context.yaml` | sub-especificación que se envió al LLM |

> La API demo tiene a propósito una inconsistencia con su contrato: devuelve `tag: null`
> aunque el contrato dice texto. Las pruebas generadas lo detectan como "posible regresión",
> que es un buen ejemplo de lo que la herramienta encuentra.

---

## 6. El experimento

### 6.1 Diseño
`benchmark/benchmark.yaml` define **5 configuraciones × 3 APIs × 5 repeticiones = 75 corridas**
(ver [sección 9](#9-configuraciones-del-experimento-y-por-qué-son-automáticas)). El orden de las
configuraciones se aleatoriza dentro de cada repetición (semilla fija), y la API se reinicia antes
de cada corrida para partir de datos limpios.

Como las APIs reales no traen un "commit con cambios", se simula un **escenario de cambio**: la
especificación vigente es la versión nueva, y la versión "anterior" se obtiene quitándole los
endpoints/campos listados en `scenario` (`remove_operations`, `remove_properties`).

### 6.2 APIs del experimento

| API | Complejidad | Operaciones | Autenticación | Cambio simulado (operaciones objetivo) | Reducción de contexto |
|---|---|---|---|---|---|
| **Swagger Petstore v3** | baja | 19 | no | 3 endpoints nuevos + campo `tags` agregado al esquema `Pet` (7 ops) | 56 % |
| **VAmPI** | media | 14 | JWT (`admin`) | 2 endpoints nuevos + 2 respuestas 401 documentadas (4 ops) | 60 % |
| **Full Stack FastAPI Template** | alta (FastAPI + PostgreSQL) | 23 | JWT (superusuario) | 2 endpoints nuevos, 1 campo, 1 parámetro y 1 respuesta (5 ops) | 67 % |

- **Petstore** se usa en varios estudios de la revisión [4], [12], [14] y tiene un bug documentado (ver piloto).
- **VAmPI** aparece en Pasca et al. [11]; se ejecuta en modo seguro (`vulnerable=0`).
- **FastAPI Template** tiene base de datos real, validaciones y roles; su base se recrea en cada corrida.

Las versiones están **fijadas en un commit** (`benchmark/setup_apis.py`) y sus contratos OpenAPI
(`benchmark/specs/`) se extrajeron de esos mismos commits.

**Cómo se simula el cambio.** La versión *nueva* del contrato es la API tal como se ejecuta, así
que todo lo que se detecta como cambio existe de verdad en la aplicación. La versión *anterior*
se obtiene deshaciendo cambios con estas reglas (sección `scenario` de cada API):
`remove_operations` (endpoints nuevos), `remove_properties` (campos nuevos), `remove_required`
(campos que pasaron a ser obligatorios), `remove_parameters` (parámetros nuevos) y
`remove_responses` (respuestas HTTP documentadas).

**Autenticación.** Antes de cada corrida el script inicia sesión (`auth` en `benchmark.yaml`) y usa
el mismo token para **A, B y C**. Las pruebas del LLM lo reciben a través de la fixture `api`, y
Schemathesis como header. El prompt de B y C incluye la misma nota de entorno (`context_note`).

**Estado limpio verificado.** Antes de cada corrida la API se recrea desde cero (contenedor o base
de datos nueva), se pueblan sus datos (`setup`) y se ejecuta una **prueba de humo** (`smoke`). Si
falla, se reintenta, y si sigue fallando no se ejecuta la corrida ni se gasta cuota.

### 6.3 Ejecutar
Con Docker Desktop abierto, **una sola vez**, prepara las APIs (descarga el código fijado y
construye las imágenes; la primera vez tarda varios minutos):
```powershell
python benchmark/setup_apis.py
```
Luego:
```powershell
# prueba corta: 1 repetición, solo Petstore
python benchmark/run_benchmark.py --apis petstore3 --reps 1

# experimento completo (reanudable: si se corta o se acaba la cuota, vuelve a ejecutarlo)
python benchmark/run_benchmark.py

# análisis estadístico
python benchmark/analyze.py benchmark/results/results.csv
```
Si cambias de modelo o de configuración, borra `benchmark\results` y empieza de cero: todas las
corridas deben hacerse en las mismas condiciones.

### 6.4 Resultados (`benchmark\results\`)
| Archivo | Contenido |
|---|---|
| `results.csv` | una fila por corrida |
| `evidencia_experimento.xlsx` | evidencia completa ([sección 7](#7-evidencia-en-excel)) |
| `analysis.md` | tablas y pruebas estadísticas para la tesis |
| `summary_*.csv`, `tests.csv` | resúmenes y pruebas de hipótesis |
| `fig_*.png` | diagramas de caja por métrica |
| `<api>\<config>_r<rep>\` | todos los archivos de cada corrida (ver tabla de la sección 5) |

Estadística: Kruskal–Wallis entre configuraciones, Mann–Whitney U por pares con corrección de
Holm, δ de Cliff como tamaño del efecto y Friedman con bloques API × repetición.

---

## 7. Evidencia en Excel

Se genera sola al terminar (o detenerse) el experimento: un Excel **general** (`evidencia_experimento.xlsx`, las 3 APIs) y **uno por API** (`evidencia_<api>.xlsx`). También puedes generarlos a mano:
```powershell
python benchmark/export_evidence.py
```

| Hoja | Qué registra |
|---|---|
| **Leeme** | descripción, modelo usado y de dónde sale cada dato |
| **Resumen** | promedios por configuración y reducción de tokens C vs. B (fórmulas) |
| **Condiciones** | modelo y parámetros del LLM, versiones de software, commits de las APIs y escenarios de cambio |
| **Corridas** | una fila por corrida: fecha, API, configuración, tests, tasa ejecutable, cobertura, tokens, costo, iteraciones, estado de la API al terminar, carpeta de evidencia |
| **Pasos** | **bitácora con hora de cada paso de cada corrida, para A, B y C**: reinicio de la API, preparación de datos, prueba de humo, login, carga de especificaciones, análisis delta, contexto enviado, generación (Schemathesis o LLM), cada ejecución de Pytest, cada reparación, versión final, cobertura y estado final |
| **Codigo_generado** | el archivo de pruebas final de cada corrida (Schemathesis en A, LLM en B y C) |
| **Trafico_HTTP** | cada petición HTTP real enviada a la API, con el test que la envió y el código de respuesta |
| **Llamadas_LLM** | cada llamada al LLM: fase (generación/reparación), tokens, latencia, si se cortó, archivos |
| **Prompts** | el **texto exacto** de cada prompt enviado y de cada respuesta recibida |
| **Casos_de_prueba** | resultado final de cada test generado |
| **Cobertura** | por operación: códigos HTTP documentados, observados y cubiertos |
| **Registro_manual** | plantilla opcional para ejecuciones hechas por una persona |

Cada fila incluye la carpeta de origen, así que cualquier dato puede verificarse contra el archivo
que lo produjo.

---

## 8. Integración con GitHub Actions

### 8.1 Subir el proyecto
1. En github.com: **+ → New repository**, nombre `deltaheal-api-testing`, **Private**, sin README.
2. En la terminal (cambia `TU_USUARIO`):
   ```powershell
   git init
   git add .
   git commit -m "Prototipo DeltaHeal"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/deltaheal-api-testing.git
   git push -u origin main
   ```
3. **Settings → Secrets and variables → Actions → New repository secret**:
   nombre `GEMINI_API_KEY`, valor tu clave.

### 8.2 Workflows incluidos
| Archivo | Cuándo corre | Qué hace |
|---|---|---|
| `.github/workflows/api-regression.yml` | en cada Pull Request que modifica la especificación | levanta la API, ejecuta DeltaHeal contra la rama base, **comenta el reporte en el PR**, sube los artefactos y marca el PR en rojo si hay posibles regresiones |
| `.github/workflows/benchmark.yml` | manual (**Actions → Benchmark experiment → Run workflow**) | ejecuta el experimento, el análisis y el Excel; los deja como artefacto descargable |
| `action.yml` | desde otros repositorios | acción reutilizable (`uses: TU_USUARIO/deltaheal-api-testing@main`) |

### 8.3 Probarlo
- **Benchmark sin gastar cuota:** Actions → Benchmark experiment → Run workflow → en *config*
  escribe `benchmark/benchmark.demo.yaml`.
- **Flujo de Pull Request:**
  ```powershell
  git checkout -b prueba-cambio
  # edita examples/demo_api/openapi_v2.yaml (p. ej. cambia un "summary") y guarda
  git commit -am "Cambio en el contrato"
  git push -u origin prueba-cambio
  ```
  En GitHub: **Compare & pull request → Create pull request**. En unos minutos aparece el
  reporte de DeltaHeal como comentario.

Para usarlo con tu propia API, en `api-regression.yml` cambia `SPEC_PATH`, `API_BASE_URL` y el paso
"Levantar API bajo prueba".

---

## 9. Configuraciones del experimento y por qué son automáticas

| Config. | `--mode` | Delta | Reparación | Qué representa |
|---|---|---|---|---|
| **A** | `traditional` | — | — | Herramienta tradicional **sin IA**: Schemathesis genera casos automáticamente a partir del contrato (property-based testing), con datos válidos e inválidos |
| **B** | `llm_full` | ✗ | ✗ | **LLM básico**: se envía la OpenAPI completa con un prompt, se toma el código tal como viene y se ejecuta |
| **C** | `deltaheal` | ✓ | ✓ | **Prototipo propuesto** |
| Ablación | `delta_only` | ✓ | ✗ | aísla el efecto del análisis delta |
| Ablación | `full_heal` | ✗ | ✓ | aísla el efecto del self-healing |

**¿Por qué A y B no las hace una persona?**

- **A** es una *herramienta* tradicional sin IA, no testing manual. Schemathesis es una herramienta
  de testing automático de APIs ampliamente usada; se ejecuta igual que la usaría un equipo en CI.
- **B** reproduce lo que hace una persona con un LLM: pegar la especificación completa, pedir las
  pruebas y ejecutarlas sin corregirlas. Se automatiza con el **mismo prompt** que C (solo cambia
  el contexto: spec completa vs. delta). Así la comparación aísla el efecto del delta y del
  self-healing, y no la habilidad de quien escribe el prompt.
- Automatizar ambas da **reproducibilidad** (las 5 repeticiones se hacen en condiciones idénticas)
  y **medición exacta** de tokens y tiempos, que en una interfaz web no se pueden medir con
  precisión.
- La **evidencia** de que se hizo así queda en el Excel: hoja **Prompts** (texto exacto de cada
  prompt y respuesta), **Llamadas_LLM** y **Casos_de_prueba**.

Si tu asesor pide además un contraste con pruebas hechas por una persona (por ejemplo, Postman a mano
o un LLM usado en el chat web), regístralo en la hoja **Registro_manual**. Tiene una fila de ejemplo
y las celdas a completar en amarillo.

---

## 10. Métricas (definición operativa)

| Métrica | Definición |
|---|---|
| **Tasa de pruebas ejecutables** | tests que corren hasta el final (pasan o fallan por aserción) / tests generados. Errores de sintaxis, colección, `NameError`, fixtures inexistentes, etc. = no ejecutables. |
| **Cobertura de respuestas HTTP** | pares (operación, código HTTP) documentados en el contrato **y** observados en el tráfico real / pares documentados. Se mide sobre las operaciones del delta, el mismo denominador para todas las configuraciones. |
| **Tokens** | entrada + salida reportados por el proveedor (incluye tokens de razonamiento), separados en generación y reparación. |
| **Costo** | tokens × precio de lista configurado. Con el nivel gratuito el gasto real es $0; se reporta el **costo equivalente**. |

---

## 11. Estructura del proyecto

```
deltaheal/                 el orquestador
  delta.py                 análisis delta de la OpenAPI (git diff + comparación por operación)
  llm.py                   clientes LLM (Gemini, Groq, Ollama, DeepSeek, OpenAI, Anthropic, mock)
  prompts.py               prompts de generación y reparación
  healer.py                bucle de auto-corrección
  patcher.py               reparación parcial (reemplaza solo los tests que fallaron)
  runner.py                ejecución de Pytest y clasificación de resultados
  pytest_plugin.py         fixture `api` + registro del tráfico HTTP
  coverage.py              cobertura de respuestas HTTP
  baseline_schemathesis.py configuración A
  orchestrator.py, cli.py  pipeline y línea de comandos
benchmark/
  benchmark.yaml           diseño del experimento (APIs, configuraciones, modelo)
  benchmark.demo.yaml      prueba del experimento sin costo
  run_benchmark.py         ejecuta el experimento
  analyze.py               análisis estadístico
  export_evidence.py       Excel de evidencias
  specs/                   especificaciones OpenAPI de las APIs
examples/demo_api/         API de demostración (FastAPI) + contratos v1 y v2
tests/                     pruebas del propio prototipo (32)
.github/workflows/         integración con GitHub Actions
```

---

## 12. Solución de problemas

| Mensaje | Solución |
|---|---|
| `No module named 'deltaheal'` | ejecuta los comandos desde la carpeta del proyecto, con el entorno activado |
| `...Activate.ps1 no se puede cargar...` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (una vez) |
| `API key not valid` / `401` / `403` | revisa `GEMINI_API_KEY` en `.env` (sin espacios ni comillas) |
| `model not found` / `404` | `python -m deltaheal models` y usa un nombre de esa lista en `benchmark.yaml` |
| `⏸ Se agotó la cuota diaria` | normal en el nivel gratuito: vuelve a ejecutar el mismo comando al día siguiente |
| `No hay ninguna API respondiendo…` | levanta la API (uvicorn o Docker) antes de ejecutar; no se gasta cuota |
| `esperando que la API responda…` (se queda ahí) | Docker Desktop no está abierto |
| `container name ... already in use` | se resuelve solo; si persiste: `docker rm -f petstore3` (o `vampi`) |
| `falta benchmark/apis/...` | ejecuta una vez `python benchmark/setup_apis.py` |
| `port is already allocated` | otro programa usa el puerto 8080 (Petstore), 5000 (VAmPI) u 8000 (FastAPI); ciérralo |
| `no se pudo iniciar sesión` | la API no terminó de arrancar; vuelve a ejecutar el benchmark (la corrida quedó pendiente) |
| "Respuestas cortadas" > 0 en el reporte | el modelo agotó su presupuesto de salida; sube `max_tokens` en `benchmark.yaml` |

---

**Limitaciones y amenazas a la validez a discutir en la tesis:** no determinismo del LLM
(mitigado con 5 repeticiones), escenarios de cambio sintéticos, posible presencia de APIs populares
como Petstore en los datos de entrenamiento del LLM, cuotas del nivel gratuito (el experimento puede
repartirse en varios días con el mismo modelo) y potencia estadística limitada con n = 5 por celda.
