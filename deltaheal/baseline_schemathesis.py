"""Configuración A: herramienta tradicional SIN IA (Schemathesis, property-based testing).

Se genera un archivo Pytest que usa la integración de Schemathesis y se ejecuta
con el MISMO runner y el MISMO plugin de tráfico que las configuraciones con LLM,
de modo que la tasa de ejecutabilidad y la cobertura HTTP se miden idénticamente.
Tokens y costo de LLM son 0 por definición.
"""

from __future__ import annotations

from pathlib import Path

# Un test Pytest por operación. Dentro, Hypothesis genera `max_examples` casos;
# las violaciones de los checks de Schemathesis se acumulan (en vez de abortar en
# la primera, que es el comportamiento por defecto) para que la herramienta
# explore todo su presupuesto de ejemplos: así la línea base no queda en
# desventaja artificial en cobertura HTTP. Al final, si hubo violaciones, el
# test falla con AssertionError (cuenta como test ejecutable con falla).
TEMPLATE = '''\
import os

import pytest
import schemathesis
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from schemathesis import GenerationMode


def _strategy(operation):
    # Datos válidos (positive) e inválidos (negative), como hace la CLI de Schemathesis.
    strategies = [operation.as_strategy(GenerationMode.POSITIVE)]
    try:
        strategies.append(operation.as_strategy(GenerationMode.NEGATIVE))
    except Exception:
        pass
    return st.one_of(*strategies)

schema = schemathesis.openapi.from_path({spec_path!r})
OPERATIONS = []
for _res in schema.get_all_operations():
    try:
        OPERATIONS.append(_res.ok())
    except Exception:  # operación que Schemathesis no puede cargar
        pass


@pytest.mark.parametrize("operation", OPERATIONS, ids=lambda op: op.label)
def test_api(operation):
    base_url = os.environ["API_BASE_URL"]
    violations = []

    @given(case=_strategy(operation))
    @settings(max_examples={max_examples}, deadline=None, database=None,
              suppress_health_check=list(HealthCheck))
    def explore(case):
        response = case.call(base_url=base_url)
        try:
            case.validate_response(response)
        except Exception as exc:  # violación de checks de Schemathesis
            violations.append(f"{{type(exc).__name__}}: {{str(exc)[:400]}}")

    explore()
    unique = sorted(set(violations))
    assert not unique, f"{{len(unique)}} violaciones distintas:\\n" + "\\n".join(unique[:10])
'''


def write_schemathesis_test(spec_path: Path, workdir: Path, max_examples: int = 25) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    f = workdir / "test_schemathesis.py"
    f.write_text(TEMPLATE.format(spec_path=str(spec_path.resolve()), max_examples=max_examples),
                 encoding="utf-8")
    return f
