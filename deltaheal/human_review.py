"""Supervisión humana: revisión interactiva de las pruebas y fallas aceptadas por el equipo.

1. Revisión antes de ejecutar (`--review`): antes de ejecutar contra la API las pruebas generadas
   o reparadas, una persona puede revisarlas, editarlas o cancelar la ejecución.

2. Fallas aceptadas (`--accepted archivo.yaml`): posibles regresiones que el equipo ya revisó y
   decidió aceptar. Siguen apareciendo en el reporte, en una sección aparte, pero no bloquean el
   Pull Request. Cada regla exige un motivo y puede tener fecha de vencimiento:

       - match: "pets_petId"        # texto en el nombre de la prueba o en el mensaje de la falla
         reason: "500 conocido; corrección planificada en el issue #12"
         until: 2026-12-31          # opcional: desde el día siguiente la regla deja de aplicarse
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


# --------------------------------------------------------------------------- #
# Fallas aceptadas
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AcceptedRule:
    match: str
    reason: str
    until: date | None = None

    def is_active(self, today: date) -> bool:
        return self.until is None or today <= self.until

    def to_dict(self) -> dict[str, Any]:
        return {"match": self.match, "reason": self.reason,
                "until": self.until.isoformat() if self.until else None}


def _parse_until(value: Any, where: str) -> date | None:
    if value is None or isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as e:
        raise ValueError(f"{where}: 'until' debe tener el formato AAAA-MM-DD") from e


def _parse_rule(item: Any, where: str) -> AcceptedRule:
    if not isinstance(item, dict) or not str(item.get("match") or "").strip():
        raise ValueError(f"{where}: falta 'match'")
    if not str(item.get("reason") or "").strip():
        raise ValueError(f"{where}: falta 'reason' (toda falla aceptada debe justificarse)")
    return AcceptedRule(str(item["match"]).strip(), str(item["reason"]).strip(),
                        _parse_until(item.get("until"), where))


def load_accepted(path: str | Path) -> list[AcceptedRule]:
    """Lee el archivo de fallas aceptadas. Lanza ValueError si el formato no es válido."""
    p = Path(path)
    if not p.exists():
        raise ValueError(f"No existe el archivo de fallas aceptadas: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or []
    if isinstance(data, dict) and "accepted" in data:
        data = data["accepted"] or []
    if not isinstance(data, list):
        raise ValueError(f"{p}: se esperaba una lista de reglas (match, reason, until)")
    return [_parse_rule(item, f"{p}, regla {n}") for n, item in enumerate(data, 1)]


def split_accepted(regressions: list[dict[str, Any]], rules: list[AcceptedRule],
                   today: date | None = None) -> tuple[list[dict], list[dict], list[dict]]:
    """Separa las posibles regresiones en (pendientes, aceptadas, reglas vencidas).

    Una regresión se acepta si el texto `match` de una regla vigente aparece (sin distinguir
    mayúsculas) en el nombre de la prueba o en el mensaje de la falla.
    """
    today = today or date.today()
    active = [r for r in rules if r.is_active(today)]
    expired = [r.to_dict() for r in rules if not r.is_active(today)]
    pending, accepted = [], []
    for reg in regressions:
        text = f"{reg.get('test', '')}\n{reg.get('message', '')}".lower()
        rule = next((r for r in active if r.match.lower() in text), None)
        if rule:
            accepted.append({**reg, "reason": rule.reason, "rule": rule.match})
        else:
            pending.append(reg)
    return pending, accepted, expired


# --------------------------------------------------------------------------- #
# Revisión interactiva en consola
# --------------------------------------------------------------------------- #

def _test_names(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [n.name for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test")]


def console_reviewer(test_file: Path, iteration: int) -> bool:
    """Muestra las pruebas y pide aprobación antes de ejecutarlas. Devuelve True para ejecutar."""
    names = _test_names(test_file.read_text(encoding="utf-8"))
    origin = "generadas por la IA" if iteration == 0 else f"reparadas por la IA (iteración {iteration})"
    lines = ["", f"  ✋ Revisión humana: pruebas {origin}", f"     Archivo: {test_file}",
             f"     {len(names)} pruebas:"]
    lines += [f"       - {n}" for n in names[:25]]
    if len(names) > 25:
        lines.append(f"       … y {len(names) - 25} más")
    lines.append("     El archivo puede editarse ahora; los cambios se usarán al ejecutar.")
    print("\n".join(lines), file=sys.stderr, flush=True)  # siempre visible, aun con --quiet
    try:
        answer = input("     Enter = ejecutar contra la API · n = cancelar: ")
    except EOFError:
        return False
    print(file=sys.stderr)
    return answer.strip().lower() not in ("n", "no")
