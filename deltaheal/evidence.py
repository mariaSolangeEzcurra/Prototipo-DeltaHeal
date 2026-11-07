"""Bitácora de pasos de cada corrida (evidencia de que cada paso se ejecutó).

Cada entrada guarda la hora, el nombre del paso, un detalle legible y, si existe,
el archivo que lo respalda. Se guarda en report.json -> "steps" y se exporta a la
hoja "Pasos" del Excel de evidencias, para las configuraciones A, B y C por igual.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class StepLog:
    def __init__(self, base_dir: Path | None = None, initial: list[dict[str, Any]] | None = None):
        self.base_dir = base_dir
        self.steps: list[dict[str, Any]] = list(initial or [])

    def add(self, paso: str, detalle: str = "", archivo: str | Path | None = None) -> None:
        if archivo is not None and self.base_dir is not None:
            try:
                archivo = Path(archivo).resolve().relative_to(self.base_dir.resolve()).as_posix()
            except ValueError:
                archivo = str(archivo)
        self.steps.append({
            "hora": datetime.now().isoformat(timespec="seconds"),
            "paso": paso,
            "detalle": detalle,
            "archivo": str(archivo) if archivo else "",
        })


def run_summary(run: Any) -> str:
    """Resumen legible de una ejecución de Pytest."""
    parts = [f"{len(run.cases)} tests ejecutados", f"{run.count('passed')} pasan",
             f"{run.count('assertion')} fallan por aserción",
             f"{run.count('runtime_error') + run.count('setup_error')} con error de código"]
    if run.collection_error:
        parts.append("ERROR DE COLECCIÓN")
    if run.count("connection_error"):
        parts.append(f"{run.count('connection_error')} sin conexión")
    return ", ".join(parts) + f" (exit={run.exit_code}, {run.duration_s:.1f}s)"
