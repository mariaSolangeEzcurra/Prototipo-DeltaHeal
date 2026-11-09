"""Asistente de configuración (`deltaheal init`): crea deltaheal.yaml a partir de unas preguntas.

Detecta los contratos OpenAPI del repositorio y la rama principal de git para proponer valores
por defecto. Con `--yes` usa esos valores sin preguntar (útil en scripts).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .config import UsageError

PROVIDERS = ("gemini", "groq", "ollama", "openai", "deepseek", "anthropic", "mock")
DEFAULT_MODELS = {"gemini": "gemini-3.8-flash", "mock": "mock-1"}
KEY_VARIABLES = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY",
                 "deepseek": "DEEPSEEK_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
SPEC_PREFIXES = ("openapi", "swagger")
SPEC_SUFFIXES = (".yaml", ".yml", ".json")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "build", "dist",
             "deltaheal-out"}

TEMPLATE = """\
# Configuración de DeltaHeal.
#   Ejecutar:            python -m deltaheal run -c {file}
#   Opciones completas:  python -m deltaheal run --help

spec_path: {spec}        # contrato OpenAPI de la API
base_ref: {base_ref}     # rama o commit contra el que se comparan los cambios
base_url: {base_url}     # URL de la API en ejecución
mode: deltaheal

provider: {provider}
model: {model}
max_heal_iterations: 3
fail_on: regression      # regression | any | never
output_dir: deltaheal-out

# Fallas revisadas y aceptadas por el equipo (opcional):
# accepted_file: deltaheal-accepted.yaml

# Autenticación: no guardar tokens en este archivo. Usar la variable de entorno
#   DELTAHEAL_AUTH_HEADER="Authorization: Bearer <token>"   o la opción --auth-header.
"""


class InitError(UsageError):
    pass


def find_spec_candidates(root: Path, max_depth: int = 4, limit: int = 10) -> list[str]:
    """Archivos con nombre openapi*/swagger* (.yaml, .yml, .json) dentro del repositorio."""
    found: list[str] = []

    def walk(folder: Path, depth: int) -> None:
        if depth > max_depth or len(found) >= limit:
            return
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir() and entry.name not in SKIP_DIRS:
                walk(entry, depth + 1)
            elif (entry.is_file() and entry.suffix.lower() in SPEC_SUFFIXES
                  and entry.name.lower().startswith(SPEC_PREFIXES)):
                found.append(entry.relative_to(root).as_posix())

    walk(root, 0)
    return found[:limit]


def default_base_ref(root: Path) -> str:
    """Rama principal del remoto (p. ej. origin/main), o origin/main si no se puede detectar."""
    try:
        out = subprocess.run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=root,
                             capture_output=True, text=True, check=False).stdout.strip()
    except OSError:
        out = ""
    return out or "origin/main"


def _interactive() -> bool:
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _ask(question: str, default: str, assume_yes: bool, choices: tuple[str, ...] | None = None) -> str:
    if assume_yes or not _interactive():
        return default
    while True:
        hint = f" [{default}]" if default else ""
        answer = input(f"{question}{hint}: ").strip() or default
        if not answer:
            print("  Valor obligatorio.")
        elif choices and answer not in choices:
            print(f"  Opciones válidas: {', '.join(choices)}")
        else:
            return answer


def _yaml_str(value: str) -> str:
    """Valor YAML entre comillas (JSON es YAML válido y escapa caracteres especiales)."""
    return json.dumps(value, ensure_ascii=False)


def run_init(path: str = "deltaheal.yaml", assume_yes: bool = False, force: bool = False) -> tuple[Path, str]:
    """Crea el archivo de configuración. Devuelve (ruta, proveedor elegido)."""
    target = Path(path)
    root = Path.cwd()
    if target.exists() and not force:
        if assume_yes or not _interactive():
            raise InitError(f"{target} ya existe. Usar --force para sobrescribirlo.")
        if input(f"{target} ya existe. ¿Sobrescribir? (s/N): ").strip().lower() not in ("s", "si", "sí"):
            raise InitError("Operación cancelada; no se modificó el archivo.")

    candidates = find_spec_candidates(root)
    if candidates and not assume_yes and _interactive():
        print("Contratos OpenAPI encontrados:")
        for c in candidates:
            print(f"  - {c}")
    spec = _ask("Ruta del contrato OpenAPI", candidates[0] if candidates else "openapi.yaml", assume_yes)
    base_url = _ask("URL de la API en ejecución", "http://localhost:8080", assume_yes)
    base_ref = _ask("Rama base para comparar cambios", default_base_ref(root), assume_yes)
    provider = _ask(f"Proveedor de IA ({' | '.join(PROVIDERS)})", "gemini", assume_yes, PROVIDERS)
    model = _ask("Modelo (lista: python -m deltaheal models)", DEFAULT_MODELS.get(provider, ""), assume_yes)
    if not model:
        raise InitError(f"Indicar el modelo para el proveedor '{provider}'.")

    target.write_text(TEMPLATE.format(file=target.as_posix(), spec=_yaml_str(spec), base_ref=_yaml_str(base_ref),
                                      base_url=_yaml_str(base_url), provider=_yaml_str(provider),
                                      model=_yaml_str(model)), encoding="utf-8")
    if not (root / spec).exists():
        print(f"Aviso: no se encontró {spec}; revisar spec_path en {target}.")
    return target, provider


def next_steps(target: Path, provider: str) -> str:
    steps = []
    if provider in KEY_VARIABLES:
        steps.append(f"Registrar la clave en .env ({KEY_VARIABLES[provider]}=...); ver .env.example.")
        steps.append(f"Verificar la conexión:  python -m deltaheal check-llm -c {target}")
    steps.append(f"Ver qué cambió:         python -m deltaheal delta -c {target}")
    steps.append(f"Ejecutar:               python -m deltaheal run -c {target}")
    return "\n".join(f"  {n}. {s}" for n, s in enumerate(steps, 1))
