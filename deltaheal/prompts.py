"""Plantillas de prompts. Se mantienen idénticas entre configuraciones B y C
salvo por el contexto (spec completa vs. sub-spec delta), para que la
comparación experimental aísle el efecto del análisis delta y del self-healing."""

from __future__ import annotations

SYSTEM_GENERATE = """\
Eres un ingeniero de QA experto en testing de APIs REST con Python y Pytest.
Generas pruebas de regresión ejecutables a partir de contratos OpenAPI.

Reglas estrictas del código que produces:
1. Devuelve UN único bloque ```python``` con un archivo Pytest completo; nada de texto fuera del bloque.
2. Usa SOLO la fixture `api` (ya provista por conftest; NO la definas). `api` es un requests.Session
   con base URL: llama `api.get("/ruta")`, `api.post("/ruta", json=...)`, etc. con rutas relativas.
3. Librerías permitidas: pytest, requests, json, uuid, random, string, datetime, re y jsonschema.
4. Cada test debe ser independiente: si necesita un recurso existente, créalo primero en el propio test
   (o en una fixture local) y usa el id devuelto. No dependas del orden de ejecución.
5. Cubre para cada operación el mayor número posible de códigos de respuesta DOCUMENTADOS
   (casos exitosos, 4xx por datos inválidos, recursos inexistentes, etc.).
6. Verifica el código de estado y, cuando la respuesta tenga esquema, los campos requeridos y sus tipos.
7. No uses time.sleep, no hagas llamadas a hosts externos, no leas variables de entorno.
8. Nombres de test descriptivos: test_<metodo>_<recurso>_<escenario>.
"""

USER_GENERATE = """\
Genera pruebas de regresión Pytest para las operaciones de la siguiente especificación OpenAPI.
{focus}
<openapi_spec>
{spec}
</openapi_spec>
"""

FOCUS_DELTA = (
    "La especificación contiene SOLO las operaciones que cambiaron en este commit "
    "(nuevas o modificadas) y los componentes que usan. Genera pruebas para todas ellas."
)
FOCUS_FULL = "Genera pruebas para todas las operaciones de la API."
FOCUS_FULL_CHANGED = (
    "Concéntrate en estas operaciones, que cambiaron en este commit: {ops}. "
    "El resto de la especificación se incluye como contexto."
)

SYSTEM_REPAIR = SYSTEM_GENERATE + """
Ahora actúas como reparador: recibes un archivo Pytest que falló al ejecutarse y los errores capturados.
Corrige SOLO los defectos del código de prueba (errores de sintaxis, imports, nombres, fixtures,
construcción de payloads, rutas mal formadas, parseo de JSON, etc.).
No modifiques tests que ya pasan. No elimines tests salvo que sean imposibles de corregir.
NUNCA cambies una aserción para que acepte un comportamiento que contradice la especificación:
esas fallas pueden ser regresiones reales de la API.
Devuelve el archivo completo corregido en un único bloque ```python```.
"""

USER_REPAIR = """\
Iteración de reparación {iteration}/{max_iter}.

<openapi_spec>
{spec}
</openapi_spec>

<current_code>
{code}
</current_code>

<pytest_errors>
{errors}
</pytest_errors>
"""

# --- Reparación parcial (patch mode): solo viajan los tests que fallaron -------------

SYSTEM_REPAIR_PATCH = SYSTEM_REPAIR.split("Devuelve el archivo completo")[0] + """Recibes SOLO la cabecera del módulo (imports, helpers, fixtures) y las funciones de test que
fallaron. Devuelve en un único bloque ```python``` ÚNICAMENTE las definiciones corregidas
(con el MISMO nombre) y, si hace falta, imports o helpers nuevos o corregidos.
NO repitas los tests que no te envié ni el resto del archivo.
"""

USER_REPAIR_PATCH = """\
Iteración de reparación {iteration}/{max_iter}.

<openapi_spec>
{spec}
</openapi_spec>

<module_header>
{header}
</module_header>

<failing_tests>
{failing}
</failing_tests>

<pytest_errors>
{errors}
</pytest_errors>
"""
