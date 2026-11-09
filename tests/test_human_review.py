"""Supervisión humana: fallas aceptadas, revisión antes de ejecutar y autenticación."""

import json
from datetime import date
from pathlib import Path

import pytest

from deltaheal.cli import exit_code
from deltaheal.config import Settings
from deltaheal.human_review import AcceptedRule, load_accepted, split_accepted
from deltaheal.pipeline import environment_note, run
from deltaheal.pytest_runner import run_pytest

ROOT = Path(__file__).resolve().parent.parent
V1, V2 = str(ROOT / "demo_api/openapi_v1.yaml"), str(ROOT / "demo_api/openapi_v2.yaml")


def _settings(url, tmp_path, **kw):
    return Settings.load(None, spec_path=V2, base_url=url, mode="deltaheal", provider="mock",
                         model="mock-1", output_dir=str(tmp_path / "out"), **kw)


# --------------------------------------------------------------------------- #
# Archivo de fallas aceptadas
# --------------------------------------------------------------------------- #

def test_load_accepted_valid_file(tmp_path):
    f = tmp_path / "accepted.yaml"
    f.write_text('- match: "pets_petId"\n  reason: "500 conocido"\n  until: 2026-12-31\n'
                 '- {match: tag, reason: "tag null aceptado"}\n', encoding="utf-8")
    rules = load_accepted(f)
    assert rules == [AcceptedRule("pets_petId", "500 conocido", date(2026, 12, 31)),
                     AcceptedRule("tag", "tag null aceptado")]


@pytest.mark.parametrize("content, error", [
    ('- match: "x"\n', "reason"),
    ('- reason: "sin match"\n', "match"),
    ('- {match: x, reason: y, until: "31/12/2026"}\n', "AAAA-MM-DD"),
    ('match: x\n', "lista"),
])
def test_load_accepted_rejects_invalid_rules(tmp_path, content, error):
    f = tmp_path / "accepted.yaml"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        load_accepted(f)


def test_load_accepted_missing_file(tmp_path):
    with pytest.raises(ValueError, match="No existe"):
        load_accepted(tmp_path / "no_existe.yaml")


def test_split_accepted_matches_active_rules_only():
    regs = [{"test": "test_get__pets_petId", "message": "assert 500 in [200]"},
            {"test": "test_post_pets", "message": "AssertionError: tag es None"}]
    rules = [AcceptedRule("PETS_PETID", "500 conocido"),
             AcceptedRule("tag es none", "vencida", until=date(2026, 1, 1))]
    pending, accepted, expired = split_accepted(regs, rules, today=date(2026, 6, 1))
    assert [r["test"] for r in pending] == ["test_post_pets"]
    assert accepted[0]["test"] == "test_get__pets_petId" and accepted[0]["reason"] == "500 conocido"
    assert expired == [{"match": "tag es none", "reason": "vencida", "until": "2026-01-01"}]


@pytest.mark.parametrize("demo_api", [True], indirect=True)
def test_accepted_failure_does_not_block(demo_api, tmp_path):
    f = tmp_path / "accepted.yaml"
    f.write_text('- {match: "pets_petId", reason: "500 conocido, issue #12"}\n', encoding="utf-8")
    s = _settings(demo_api, tmp_path, accepted_file=str(f))
    r = run(s, old_spec_path=V1)
    assert r["assertion_failures"] == 1           # la métrica no cambia
    assert r["possible_regressions"] == []        # pero ya no bloquea
    assert r["accepted_failures"][0]["reason"] == "500 conocido, issue #12"
    assert exit_code(s, r) == 0
    assert "Fallas aceptadas por el equipo" in (tmp_path / "out/deltaheal/report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("demo_api", [True], indirect=True)
def test_regression_blocks_without_accepted_file(demo_api, tmp_path):
    s = _settings(demo_api, tmp_path)
    assert exit_code(s, run(s, old_spec_path=V1)) == 1


# --------------------------------------------------------------------------- #
# Revisión humana antes de ejecutar
# --------------------------------------------------------------------------- #

def test_reviewer_can_edit_tests_before_execution(demo_api, tmp_path):
    calls = []

    def reviewer(test_file: Path, iteration: int) -> bool:
        calls.append(iteration)
        if iteration == 0:
            with test_file.open("a", encoding="utf-8") as fh:
                fh.write("\n\ndef test_added_by_reviewer(api):\n    assert api.get('/pets').status_code == 200\n")
        return True

    r = run(_settings(demo_api, tmp_path), old_spec_path=V1, reviewer=reviewer)
    assert calls == [0, 1]                        # generación + 1 reparación
    assert r["human_review"][0] == {"iteration": 0, "approved": True, "edited": True}
    assert any(c["test"].endswith("test_added_by_reviewer") and c["outcome"] == "passed" for c in r["test_cases"])


def test_reviewer_can_cancel_before_any_request(demo_api, tmp_path):
    s = _settings(demo_api, tmp_path)
    r = run(s, old_spec_path=V1, reviewer=lambda test_file, iteration: False)
    assert r["status"] == "review_cancelled" and r["llm_calls"] == 1
    assert (tmp_path / "out/deltaheal/http_final.jsonl").read_text(encoding="utf-8") == ""
    assert exit_code(s, r) == 5


# --------------------------------------------------------------------------- #
# Autenticación
# --------------------------------------------------------------------------- #

def test_auth_header_validation():
    with pytest.raises(ValueError, match="Nombre: valor"):
        Settings.load(None, auth_header="token-sin-nombre")
    s = Settings.load(None, auth_header="Authorization: Bearer abc")
    assert s.auth_header_name() == "Authorization"
    assert "YA está autenticada" in environment_note(s)
    assert environment_note(Settings.load(None, auth_header="")) == ""


def test_auth_header_reaches_api_fixture(tmp_path):
    test_file = tmp_path / "test_auth.py"
    test_file.write_text("def test_header(api):\n    assert api.headers['X-Token'] == 'abc 123'\n", encoding="utf-8")
    r = run_pytest(test_file, tmp_path, "http://127.0.0.1:9", tmp_path / "http.jsonl",
                   extra_env={"DELTAHEAL_AUTH_HEADER": "X-Token: abc 123"}, junit_name="junit.xml")
    assert r.count("passed") == 1, json.dumps([c.__dict__ for c in r.cases])
