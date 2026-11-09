"""Línea de comandos: ayuda, versión, delta, init, validaciones y demostración."""

import json
from pathlib import Path

import pytest

from deltaheal import __version__
from deltaheal.cli import main
from deltaheal.config import Settings

ROOT = Path(__file__).resolve().parent.parent
V1, V2 = str(ROOT / "demo_api/openapi_v1.yaml"), str(ROOT / "demo_api/openapi_v2.yaml")


def test_version(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--version"])
    assert e.value.code == 0 and capsys.readouterr().out.strip() == f"deltaheal {__version__}"


def test_help_lists_commands_and_exit_codes(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    for text in ("run", "delta", "demo", "init", "check-llm", "models", "códigos de salida"):
        assert text in out


def test_no_command_prints_help(capsys):
    assert main([]) == 2
    assert "uso: deltaheal" in capsys.readouterr().out


def test_delta_readable_output(capsys):
    assert main(["delta", "--spec", V2, "--old-spec", V1]) == 0
    out = capsys.readouterr().out
    assert "nuevo       PATCH   /pets/{petId}" in out
    assert "1 nuevo · 3 modificados · 0 eliminados · 1 sin cambios" in out
    assert "DELETE" not in out


def test_delta_json_output(capsys):
    assert main(["delta", "--spec", V2, "--old-spec", V1, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["added"] == ["PATCH /pets/{petId}"] and data["unchanged_count"] == 1


def test_delta_without_changes(capsys):
    assert main(["delta", "--spec", V2, "--old-spec", V2]) == 0
    assert "El contrato no cambió" in capsys.readouterr().out


def test_missing_spec_is_reported_without_traceback(capsys):
    assert main(["delta", "--spec", "no_existe.yaml", "--old-spec", V1]) == 2
    assert "❌" in capsys.readouterr().err


def test_missing_config_file(capsys):
    assert main(["run", "-c", "no_existe.yaml"]) == 2
    assert "No existe el archivo de configuración" in capsys.readouterr().err


def test_invalid_auth_header(capsys):
    assert main(["run", "--spec", V2, "--old-spec", V1, "--auth-header", "token-sin-nombre"]) == 2
    assert "Nombre: valor" in capsys.readouterr().err


def test_review_requires_interactive_terminal(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["run", "--spec", V2, "--old-spec", V1, "--review"]) == 2
    assert "terminal interactiva" in capsys.readouterr().err


def test_init_creates_loadable_config(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "openapi.yaml").write_text("openapi: 3.0.0\npaths: {}\n", encoding="utf-8")
    assert main(["init", "--yes"]) == 0
    assert "Configuración creada" in capsys.readouterr().out
    s = Settings.load("deltaheal.yaml")
    assert (s.spec_path, s.provider, s.model, s.mode) == ("api/openapi.yaml", "gemini", "gemini-3.8-flash", "deltaheal")
    # no sobrescribe sin --force
    assert main(["init", "--yes"]) == 2
    assert "--force" in capsys.readouterr().err
    assert main(["init", "--yes", "--force"]) == 0


def test_demo_runs_both_scenarios(tmp_path, capsys):
    pytest.importorskip("fastapi")
    assert main(["demo", "--quiet", "--output-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "sin regresiones ✅" in out and "1 posible regresión detectada" in out
    normal = json.loads((tmp_path / "1_normal" / "report.json").read_text(encoding="utf-8"))
    regression = json.loads((tmp_path / "2_regression" / "report.json").read_text(encoding="utf-8"))
    assert normal["possible_regressions"] == [] and normal["executable_rate"] == 1.0
    assert len(regression["possible_regressions"]) == 1
