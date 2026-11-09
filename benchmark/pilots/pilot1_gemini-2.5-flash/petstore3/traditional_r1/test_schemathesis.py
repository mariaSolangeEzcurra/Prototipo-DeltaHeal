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

schema = schemathesis.openapi.from_path('D:\\Tareas\\deltaheal-api-testing\\deltaheal-api-testing\\benchmark\\results\\petstore3\\traditional_r1\\spec_for_schemathesis.yaml')
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
    @settings(max_examples=25, deadline=None, database=None,
              suppress_health_check=list(HealthCheck))
    def explore(case):
        response = case.call(base_url=base_url)
        try:
            case.validate_response(response)
        except Exception as exc:  # violación de checks de Schemathesis
            violations.append(f"{type(exc).__name__}: {str(exc)[:400]}")

    explore()
    unique = sorted(set(violations))
    assert not unique, f"{len(unique)} violaciones distintas:\n" + "\n".join(unique[:10])
