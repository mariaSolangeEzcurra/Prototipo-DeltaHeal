"""DeltaHeal: pruebas de regresión de APIs REST escritas por una IA, solo para lo que cambió.

Módulos, en el orden en que se usan (ver pipeline.py):
- spec_loader:          carga el contrato OpenAPI desde un archivo o desde git.
- delta:                compara dos versiones del contrato endpoint por endpoint.
- prompts, llm:         instrucciones para la IA y clientes de cada proveedor (Gemini, Groq, mock…).
- generated_code:       extrae el código Python de la respuesta de la IA y revisa su sintaxis.
- pytest_runner:        ejecuta las pruebas y clasifica cada resultado.
- pytest_plugin:        fixture `api` y registro de cada petición HTTP.
- self_healing:         bucle que repara las pruebas con errores de código.
- partial_repair:       reenvía a la IA solo las pruebas que fallaron (ahorra tokens).
- http_coverage:        qué respuestas documentadas se observaron de verdad.
- schemathesis_baseline: modo `traditional`, pruebas sin IA para comparar.
- report, step_log:     reporte final y bitácora de pasos.
- pipeline, cli, config: el flujo completo, los comandos y la configuración.
"""

__version__ = "0.1.0"
