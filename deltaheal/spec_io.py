"""Carga de especificaciones OpenAPI desde disco o desde una referencia de git."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml


class GitError(RuntimeError):
    pass


def _git(args: list[str], cwd: str | Path) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )
    if proc.returncode != 0:
        raise GitError(f"git {' '.join(args)} falló: {proc.stderr.strip()}")
    return proc.stdout


def parse_spec_text(text: str) -> dict[str, Any]:
    """Parsea YAML o JSON (JSON es un subconjunto de YAML, pero json es más rápido)."""
    text = text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        return json.loads(text)
    data = yaml.safe_load(text)
    return data or {}


def load_spec_file(path: str | Path) -> dict[str, Any]:
    return parse_spec_text(Path(path).read_text(encoding="utf-8"))


def repo_root(cwd: str | Path = ".") -> Path:
    return Path(_git(["rev-parse", "--show-toplevel"], cwd).strip())


def load_spec_at_ref(spec_path: str, ref: str, cwd: str | Path = ".") -> dict[str, Any]:
    """Devuelve la spec tal como estaba en `ref`. Si no existía, devuelve {}."""
    root = repo_root(cwd)
    rel = Path(spec_path)
    if rel.is_absolute():
        rel = rel.relative_to(root)
    try:
        text = _git(["show", f"{ref}:{rel.as_posix()}"], root)
    except GitError:
        return {}
    return parse_spec_text(text)


def git_spec_changed(spec_path: str, base_ref: str, head_ref: str | None, cwd: str | Path = ".") -> bool:
    """`git diff --quiet` sobre el archivo de la spec. head_ref=None compara con el working tree."""
    args = ["diff", "--quiet", base_ref]
    if head_ref:
        args.append(head_ref)
    args += ["--", spec_path]
    proc = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    if proc.returncode not in (0, 1):
        raise GitError(proc.stderr.strip())
    return proc.returncode == 1


def git_spec_diff_text(spec_path: str, base_ref: str, head_ref: str | None, cwd: str | Path = ".") -> str:
    """Hunks de `git diff` (solo para trazabilidad en el reporte, no se envían al LLM)."""
    args = ["diff", "--unified=2", base_ref]
    if head_ref:
        args.append(head_ref)
    args += ["--", spec_path]
    try:
        return _git(args, cwd)
    except GitError:
        return ""


def dump_spec(spec: dict[str, Any], fmt: str = "yaml") -> str:
    if fmt == "json":
        return json.dumps(spec, indent=1, ensure_ascii=False)
    return yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=120)
