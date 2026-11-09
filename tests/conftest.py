"""Fixtures compartidas: la API de ejemplo en ejecución (con o sin regresión simulada)."""

from pathlib import Path

import pytest

from deltaheal.demo import demo_api as start_demo_api
from deltaheal.demo import free_port

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def demo_api(request, tmp_path):
    """URL de la API de ejemplo. Con `indirect=True` y valor True, GET /pets/{petId} responde 500."""
    pytest.importorskip("fastapi")
    regression = getattr(request, "param", False)
    with start_demo_api(ROOT, free_port(), regression, tmp_path / "demo_api.log") as url:
        yield url
