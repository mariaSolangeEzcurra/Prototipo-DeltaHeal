"""DeltaHeal: pruebas de regresión de APIs REST generadas con IA, solo para lo que cambió.

Módulos, en el orden en que se usan (ver pipeline.py):
- spec_loader:           carga el contrato OpenAPI desde un archivo o desde git.
- delta:                 compara dos versiones del contrato endpoint por endpoint.
- prompts, llm:          instrucciones para el modelo y clientes de cada proveedor de IA.
- generated_code:        extrae el código Python de la respuesta del modelo y revisa su sintaxis.
- pytest_runner:         ejecuta las pruebas y clasifica cada resultado.
- pytest_plugin:         fixture `api` y registro de cada petición HTTP.
- self_healing:          bucle que repara las pruebas con errores de código.
- partial_repair:        reenvía al modelo solo las pruebas que fallaron (ahorra tokens).
- http_coverage:         respuestas documentadas que se observaron en el tráfico real.
- human_review:          revisión humana antes de ejecutar y fallas aceptadas por el equipo.
- schemathesis_baseline: modo `traditional`, pruebas sin IA usadas como referencia.
- report, step_log:      reporte final y bitácora de etapas.
- pipeline, config:      el flujo completo y la configuración.
- cli, progress, demo, init_config: comandos, progreso en consola, demostración y asistente.
"""

__version__ = "0.2.0"
