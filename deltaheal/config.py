"""Configuración del orquestador (archivo YAML + overrides por CLI / variables de entorno)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

import yaml

# Configuraciones experimentales.
#   traditional : A — Schemathesis, sin IA.
#   llm_full    : B — LLM básico: spec OpenAPI completa, una sola llamada, sin reparación.
#   deltaheal   : C — Prototipo: análisis delta + self-healing loop.
# Ablaciones opcionales (permiten atribuir el efecto a cada componente):
#   delta_only  : delta sin self-healing.
#   full_heal   : spec completa con self-healing.
MODES = {
    "traditional": {"llm": False, "delta": True,  "heal": False},
    "llm_full":    {"llm": True,  "delta": False, "heal": False},
    "deltaheal":   {"llm": True,  "delta": True,  "heal": True},
    "delta_only":  {"llm": True,  "delta": True,  "heal": False},
    "full_heal":   {"llm": True,  "delta": False, "heal": True},
}


def load_dotenv(path: str | Path = ".env") -> None:
    """Carga variables CLAVE=valor desde un archivo .env (sin sobrescribir las ya definidas)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class Settings:
    spec_path: str = "openapi.yaml"
    base_ref: str = "origin/main"
    head_ref: str | None = None          # None = working tree
    base_url: str = "http://localhost:8080"
    mode: str = "deltaheal"

    provider: str = "gemini"              # gemini | groq | ollama | deepseek | openai | anthropic | mock
    model: str = "gemini-2.5-flash"
    llm_rpm: float | None = None          # llamadas/minuto (None = valor seguro del preset)
    llm_base_url: str | None = None
    temperature: float = 0.0
    max_tokens: int = 32000               # incluye el "pensamiento" de modelos de razonamiento
    reasoning_effort: str | None = None   # low | medium | high | none | "" (None = preset)
    seed: int | None = 42

    # USD por millón de tokens. Con el nivel gratuito pagas 0, pero conviene poner el precio de
    # LISTA de la capa de pago del mismo modelo para reportar un "costo equivalente" en la tesis.
    price_input_per_mtok: float = 0.0
    price_output_per_mtok: float = 0.0

    max_heal_iterations: int = 3
    heal_policy: str = "errors"           # errors | all
    repair_mode: str = "patch"            # patch: solo tests que fallaron | full: archivo completo
    full_focus_changed: bool = False      # llm_full: indicar al LLM qué endpoints cambiaron
    coverage_scope: str = "delta"         # delta | all
    traditional_scope: str = "delta"      # delta | all  (operaciones que prueba Schemathesis)
    schemathesis_examples: int = 25
    pytest_timeout: int = 60
    spec_format: str = "yaml"             # formato en que se envía la spec al LLM

    output_dir: str = "deltaheal-out"
    fail_on: str = "regression"           # regression | any | never

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None, **overrides: Any) -> "Settings":
        data: dict[str, Any] = {}
        if path and Path(path).exists():
            data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        env_map = {
            "DELTAHEAL_PROVIDER": "provider", "DELTAHEAL_MODEL": "model",
            "DELTAHEAL_LLM_BASE_URL": "llm_base_url", "API_BASE_URL": "base_url",
            "DELTAHEAL_BASE_REF": "base_ref",
        }
        for env, key in env_map.items():
            if os.getenv(env):
                data[key] = os.environ[env]
        data.update({k: v for k, v in overrides.items() if v is not None})
        known = {f.name for f in fields(cls)}
        extra = {k: v for k, v in data.items() if k not in known}
        s = cls(**{k: v for k, v in data.items() if k in known})
        s.extra.update(extra)
        if s.mode not in MODES:
            raise ValueError(f"mode inválido: {s.mode}. Opciones: {', '.join(MODES)}")
        return s
