"""Demostración guiada (`deltaheal demo`): API de ejemplo y dos escenarios en un solo comando.

  Escenario 1 · El contrato cambia (v1 → v2) y la API cumple el contrato: no hay regresiones.
  Escenario 2 · Mismo cambio, pero la API introduce un error (500): se reporta como regresión.

Inicia la API de ejemplo (demo_api/) en un puerto libre, ejecuta el flujo completo en cada
escenario y detiene la API al terminar. Con el proveedor simulado (`mock`, por defecto) no requiere
conexión a internet ni clave de API.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import requests

from .config import Settings, UsageError
from .pipeline import run
from .progress import progress
from .report import render_markdown

SCENARIOS = {
    "normal": ("Cambio en el contrato con la API funcionando correctamente",
               "El contrato v2 agrega PATCH /pets/{petId} y el campo 'age'. La API cumple el contrato.",
               False),
    "regression": ("Cambio en el contrato con una regresión en la API",
                   "Mismo cambio, pero GET /pets/{petId} responde 500 (error simulado en la API).",
                   True),
}


class DemoError(UsageError):
    pass


def find_project_root() -> Path:
    """Carpeta que contiene demo_api/ (raíz del repositorio)."""
    for base in (Path(__file__).resolve().parent.parent, Path.cwd()):
        if (base / "demo_api" / "app.py").exists():
            return base
    raise DemoError("No se encontró la carpeta demo_api/. Ejecutar el comando desde la raíz del repositorio.")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def demo_api(root: Path, port: int, regression: bool, log_file: Path) -> Iterator[str]:
    """Inicia la API de ejemplo en segundo plano y la detiene al salir."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError as e:
        raise DemoError("Faltan dependencias de la API de ejemplo: pip install fastapi uvicorn") from e
    url = f"http://127.0.0.1:{port}"
    env = dict(os.environ, DEMO_REGRESSION="1" if regression else "0")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "demo_api.app:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "warning"],
            cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            _wait_until_ready(proc, url, log_file)
            yield url
        finally:
            proc.terminate()
            try:
                proc.wait(10)
            except subprocess.TimeoutExpired:
                proc.kill()


def _wait_until_ready(proc: subprocess.Popen, url: str, log_file: Path, timeout_s: float = 20.0) -> None:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if proc.poll() is not None:
            raise DemoError(f"La API de ejemplo no pudo iniciar (ver {log_file}).")
        try:
            requests.get(url + "/pets", timeout=1)
            return
        except requests.RequestException:
            time.sleep(0.3)
    raise DemoError(f"La API de ejemplo no respondió en {timeout_s:.0f} s (ver {log_file}).")


def _display_path(path: Path) -> str:
    """Ruta relativa al directorio actual cuando es posible (mensajes más legibles)."""
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def _banner(number: int, total: int, title: str, detail: str) -> None:
    rule = "═" * 78
    print(f"\n{rule}\n Escenario {number} de {total} · {title}\n {detail}\n{rule}\n", flush=True)


def _summary_line(number: int, res: dict[str, Any]) -> str:
    regs = res.get("possible_regressions") or []
    d = res.get("delta") or {}
    ops = len(d.get("added", [])) + len(d.get("modified", []))
    repairs = res.get("heal_iterations", 0)
    text = (f"  Escenario {number}: {ops} endpoints analizados · "
            f"{res.get('executable_tests', 0)}/{res.get('generated_tests', 0)} pruebas ejecutables · "
            + ("1 reparación automática" if repairs == 1 else f"{repairs} reparaciones automáticas") + " · ")
    if res.get("status") != "ok":
        return text + f"estado: {res.get('status')}"
    if not regs:
        return text + "sin regresiones ✅"
    found = "1 posible regresión detectada" if len(regs) == 1 else f"{len(regs)} posibles regresiones detectadas"
    return text + found + " ⚠️"


def run_demo(provider: str = "mock", model: str | None = None, llm_base_url: str | None = None,
             port: int | None = None, output_dir: str = "deltaheal-out/demo",
             scenarios: list[str] | None = None, pause: bool = False) -> int:
    root = find_project_root()
    scenarios = scenarios or list(SCENARIOS)
    spec_v1 = _display_path(root / "demo_api" / "openapi_v1.yaml")
    spec_v2 = _display_path(root / "demo_api" / "openapi_v2.yaml")
    out = Path(output_dir)
    if model is None:
        if provider not in ("mock", "gemini"):
            raise DemoError(f"Indicar --model para el proveedor '{provider}' (ver: python -m deltaheal models).")
        model = "mock-1" if provider == "mock" else Settings().model
    results: list[tuple[int, dict[str, Any]]] = []

    for number, key in enumerate(scenarios, 1):
        title, detail, regression = SCENARIOS[key]
        if pause and number > 1:
            input("\nPresione Enter para continuar con el siguiente escenario…")
        _banner(number, len(scenarios), title, detail)
        with demo_api(root, port or free_port(), regression, out / f"api_{key}.log") as url:
            progress.message(f"  • API de ejemplo en ejecución: {url}")
            s = Settings.load(None, spec_path=spec_v2, base_url=url, mode="deltaheal",
                              provider=provider, model=model, llm_base_url=llm_base_url,
                              output_dir=str(out), auth_header="")
            res = run(s, old_spec_path=spec_v1, run_id=f"{number}_{key}")
        print("\n" + render_markdown(res), flush=True)
        results.append((number, res))

    print("Resumen de la demostración", flush=True)
    for number, res in results:
        print(_summary_line(number, res), flush=True)
    print(f"  Archivos generados: {_display_path(out)}", flush=True)
    return 0
