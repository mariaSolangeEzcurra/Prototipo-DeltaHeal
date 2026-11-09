"""Ejecución de Pytest en subproceso y clasificación de resultados.

Clasificación de cada caso (base de la métrica "tasa de pruebas ejecutables"):
  passed           -> ejecutable
  assertion        -> ejecutable (el test corrió; la API no cumplió lo esperado)
  runtime_error    -> NO ejecutable (NameError, TypeError, KeyError, fixture inexistente…)
  setup_error      -> NO ejecutable (error en setup/teardown de fixtures)
  connection_error -> NO ejecutable, pero atribuible al entorno (API caída)
  skipped          -> no cuenta como ejecutable
  collection_error -> el módulo no se pudo importar: todos sus tests son no ejecutables
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# Excepciones que indican que el test SÍ se ejecutó y lo que falló fue la verificación.
ASSERTION_LIKE = (
    "AssertionError", "assert ", "Failed:", "FailureGroup", "CheckFailed",
    "ValidationError",          # jsonschema.validate sobre la respuesta
    "schemathesis.",            # fallos de checks de Schemathesis
    "UndefinedStatusCode", "UnsupportedMethodResponse", "ServerError", "JsonSchemaError",
    "RejectedPositiveData", "AcceptedNegativeData", "MissingHeaders", "IgnoredAuth",
)
CONNECTION_LIKE = ("ConnectionError", "ConnectTimeout", "ReadTimeout", "Max retries exceeded")


@dataclass
class CaseResult:
    nodeid: str
    outcome: str  # passed | assertion | runtime_error | setup_error | connection_error | skipped
    message: str = ""
    details: str = ""

    @property
    def executable(self) -> bool:
        return self.outcome in ("passed", "assertion")


@dataclass
class RunResult:
    exit_code: int
    duration_s: float
    cases: list[CaseResult] = field(default_factory=list)
    collection_error: str | None = None
    stdout_tail: str = ""

    def count(self, outcome: str) -> int:
        return sum(1 for c in self.cases if c.outcome == outcome)

    @property
    def executed(self) -> int:
        return sum(1 for c in self.cases if c.executable)

    @property
    def broken(self) -> list[CaseResult]:
        return [c for c in self.cases if c.outcome in ("runtime_error", "setup_error")]

    @property
    def has_code_defects(self) -> bool:
        return bool(self.collection_error) or bool(self.broken)


_EXC_RE = re.compile(r"^([A-Za-z_][\w.]*)(?::|\(|\s*$)")
_E_LINE_RE = re.compile(r"^E\s+([A-Za-z_][\w.]*(?:Error|Exception|Failed|Group|Failure))\b", re.M)


def _classify(kind: str, message: str, text: str) -> str:
    blob = f"{message}\n{text}"
    if any(s in blob for s in CONNECTION_LIKE):
        return "connection_error"
    if kind == "error":
        return "setup_error"
    head = message.strip()
    if head.startswith(("assert", "AssertionError", "Failed")):
        return "assertion"
    if "schemathesis.openapi.checks." in blob or "schemathesis.core.failures." in blob:
        return "assertion"
    m = _EXC_RE.match(head)
    exc = m.group(1) if m else ""
    if not exc:
        found = _E_LINE_RE.findall(text)
        exc = found[-1] if found else ""
        if not exc and re.search(r"^E\s+assert ", text, re.M):
            return "assertion"
    if exc and any(tok in exc for tok in ASSERTION_LIKE):
        return "assertion"
    return "runtime_error"


def parse_junit(xml_path: Path) -> tuple[list[CaseResult], str | None]:
    if not xml_path.exists():
        return [], "No se generó el reporte JUnit"
    root = ET.parse(xml_path).getroot()
    cases: list[CaseResult] = []
    collection_error: str | None = None
    for tc in root.iter("testcase"):
        classname = tc.get("classname", "")
        name = tc.get("name", "")
        nodeid = f"{classname}::{name}" if classname else name
        fail = tc.find("failure")
        err = tc.find("error")
        skip = tc.find("skipped")
        if err is not None and (not classname or "collection failure" in (err.get("message") or "")):
            collection_error = (err.get("message") or "") + "\n" + (err.text or "")
            continue
        if fail is not None:
            msg, txt = fail.get("message") or "", fail.text or ""
            cases.append(CaseResult(nodeid, _classify("failure", msg, txt), msg, txt))
        elif err is not None:
            msg, txt = err.get("message") or "", err.text or ""
            cases.append(CaseResult(nodeid, _classify("error", msg, txt), msg, txt))
        elif skip is not None:
            cases.append(CaseResult(nodeid, "skipped", skip.get("message") or ""))
        else:
            cases.append(CaseResult(nodeid, "passed"))
    return cases, collection_error


def run_pytest(test_file: Path, workdir: Path, base_url: str, http_log: Path,
               timeout_per_test: int = 60, global_timeout: int = 900,
               extra_env: dict[str, str] | None = None, junit_name: str | None = None) -> RunResult:
    test_file, workdir, http_log = test_file.resolve(), workdir.resolve(), http_log.resolve()
    junit = workdir / (junit_name or f"junit_{test_file.stem}_{int(time.time()*1000)}.xml")
    junit.unlink(missing_ok=True)  # evita leer el resultado de una ejecución anterior
    env = os.environ.copy()
    env.update({
        "API_BASE_URL": base_url,
        "DELTAHEAL_HTTP_LOG": str(http_log),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    })
    if extra_env:
        env.update(extra_env)
    # El plugin se carga desde el paquete instalado / PYTHONPATH del proyecto.
    pkg_root = str(Path(__file__).resolve().parent.parent)
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [
        sys.executable, "-m", "pytest", str(test_file),
        "-p", "deltaheal.pytest_plugin",
        "-p", "no:cacheprovider",
        f"--junitxml={junit}",
        "-o", "junit_family=xunit2",
        "-q", "--tb=short", "--no-header", "-rN",
        "--rootdir", str(workdir),
    ]
    try:
        import pytest_timeout  # noqa: F401
        cmd.append(f"--timeout={timeout_per_test}")
    except ImportError:
        pass
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=global_timeout)
        code, out = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        code, out = 124, f"Timeout global de pytest ({global_timeout}s)\n{e.stdout or ''}"
    dt = time.perf_counter() - t0
    cases, coll_err = parse_junit(junit)
    if code == 2 and not coll_err and not cases:
        coll_err = out[-3000:]
    if code in (3, 4) and not cases:  # error interno / de uso
        coll_err = coll_err or out[-3000:]
    return RunResult(code, dt, cases, coll_err, out[-4000:])


def format_errors_for_llm(run: RunResult, max_cases: int = 12, max_chars: int = 1500) -> str:
    """Resumen compacto de los errores para el prompt de reparación (controla tokens)."""
    parts: list[str] = []
    if run.collection_error:
        parts.append("## ERROR DE COLECCIÓN (el archivo no se pudo importar/colectar)\n"
                     + run.collection_error.strip()[-max_chars:])
    for c in run.broken[:max_cases]:
        parts.append(f"## {c.nodeid} [{c.outcome}]\n{c.message.strip()}\n{c.details.strip()[-max_chars:]}")
    extra = len(run.broken) - max_cases
    if extra > 0:
        parts.append(f"... y {extra} tests más con errores similares.")
    return "\n\n".join(parts) or run.stdout_tail[-max_chars:]


def format_assertions_for_llm(run: RunResult, max_cases: int = 12, max_chars: int = 800) -> str:
    fails = [c for c in run.cases if c.outcome == "assertion"][:max_cases]
    return "\n\n".join(f"## {c.nodeid} [assertion]\n{c.message.strip()}\n{c.details.strip()[-max_chars:]}"
                       for c in fails)
