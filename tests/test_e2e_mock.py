"""Prueba de punta a punta: API demo real + LLM simulado (sin costo, sin red externa)."""

from pathlib import Path

import pytest

from deltaheal.config import Settings
from deltaheal.demo import free_port
from deltaheal.pipeline import run

ROOT = Path(__file__).resolve().parent.parent
pytest.importorskip("fastapi")


def _settings(url, tmp_path, mode):
    return Settings.load(None, spec_path=str(ROOT / "demo_api/openapi_v2.yaml"), base_url=url,
                         mode=mode, provider="mock", model="mock-1", output_dir=str(tmp_path))


def test_self_healing_repairs_injected_error(demo_api, tmp_path):
    r = run(_settings(demo_api, tmp_path, "deltaheal"),
            old_spec_path=str(ROOT / "demo_api/openapi_v1.yaml"))
    assert r["executable_rate_before_heal"] < 1.0
    assert r["executable_rate"] == 1.0
    assert r["heal_iterations"] == 1
    assert r["llm_calls"] == 2
    assert r["target_operations"] and "DELETE /pets/{petId}" not in r["target_operations"]


def test_without_healing_error_remains(demo_api, tmp_path):
    r = run(_settings(demo_api, tmp_path, "llm_full"),
            old_spec_path=str(ROOT / "demo_api/openapi_v1.yaml"))
    assert r["runtime_errors"] == 1 and r["heal_iterations"] == 0


def test_no_contract_change_spends_zero_tokens(demo_api, tmp_path):
    r = run(_settings(demo_api, tmp_path, "deltaheal"),
            old_spec_path=str(ROOT / "demo_api/openapi_v2.yaml"))
    assert r["status"] == "no_contract_changes" and r["total_tokens"] == 0


@pytest.mark.parametrize("demo_api", [True], indirect=True)
def test_regression_is_reported_not_healed(demo_api, tmp_path):
    r = run(_settings(demo_api, tmp_path, "deltaheal"),
            old_spec_path=str(ROOT / "demo_api/openapi_v1.yaml"))
    assert r["assertion_failures"] >= 1
    assert any(x["test"].endswith("pets_petId") and "get" in x["test"] for x in r["possible_regressions"])
    assert "GET /pets/{petId}" in r["coverage"]["undocumented_observed"]


def test_api_down_spends_zero_tokens(tmp_path):
    r = run(_settings(f"http://127.0.0.1:{free_port()}", tmp_path, "deltaheal"),
            old_spec_path=str(ROOT / "demo_api/openapi_v1.yaml"))
    assert r["status"] == "api_unreachable" and r["total_tokens"] == 0 and r["llm_calls"] == 0
