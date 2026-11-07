"""DeltaHeal: orquestador de testing de regresión de APIs REST con LLMs.

Componentes principales:
- delta:       análisis delta de la especificación OpenAPI vía git diff.
- llm:         clientes LLM (OpenAI-compatible, Anthropic, mock offline).
- generator:   generación de código Pytest a partir de un (sub)contrato.
- runner:      ejecución de Pytest y parseo de resultados JUnit.
- healer:      bucle de auto-corrección (self-healing loop).
- coverage:    cobertura de respuestas HTTP documentadas vs. observadas.
- orchestrator: pipeline completo y configuraciones experimentales.
"""

__version__ = "0.1.0"
