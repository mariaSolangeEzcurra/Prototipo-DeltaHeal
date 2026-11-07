"""Pipeline principal: delta → generación → self-healing → ejecución → métricas."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import prompts
from .baseline_schemathesis import write_schemathesis_test
from .codegen import static_check
from .config import MODES, Settings
from .coverage import compute_coverage
from .delta import DeltaResult, OperationKey, build_subspec, compute_delta, iter_operations
from .evidence import StepLog, run_summary
from .healer import Ledger, generate_and_heal
from .llm import make_client
from .runner import run_pytest
import requests

from .spec_io import (dump_spec, git_spec_changed, git_spec_diff_text, load_spec_at_ref,
                      load_spec_file)


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _load_specs(s: Settings, old_spec_path: str | None) -> tuple[dict, dict, bool, str]:
    new = load_spec_at_ref(s.spec_path, s.head_ref) if s.head_ref else load_spec_file(s.spec_path)
    if old_spec_path:
        return load_spec_file(old_spec_path), new, True, ""
    old = load_spec_at_ref(s.spec_path, s.base_ref)
    changed = git_spec_changed(s.spec_path, s.base_ref, s.head_ref)
    diff = git_spec_diff_text(s.spec_path, s.base_ref, s.head_ref)
    return old, new, changed, diff


def run(s: Settings, old_spec_path: str | None = None, run_id: str | None = None,
        prior_steps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    flags = MODES[s.mode]
    out = (Path(s.output_dir) / (run_id or s.mode)).resolve()
    out.mkdir(parents=True, exist_ok=True)
    log = StepLog(out, prior_steps)
    log.add("Inicio de la corrida", f"configuración={s.mode}; modelo={s.model if flags['llm'] else 'sin LLM'}; "
            f"delta={'sí' if flags['delta'] else 'no'}; self-healing={'sí' if flags['heal'] else 'no'}")

    old, new, file_changed, diff_text = _load_specs(s, old_spec_path)
    (out / "spec.git.diff").write_text(diff_text, encoding="utf-8")
    (out / "spec_base.yaml").write_text(dump_spec(old), encoding="utf-8")
    (out / "spec_head.yaml").write_text(dump_spec(new), encoding="utf-8")
    log.add("Carga de especificaciones", f"versión base: {old_spec_path or s.base_ref}; versión nueva: "
            f"{s.head_ref or s.spec_path}; ¿cambió el contrato?: {'sí' if file_changed else 'no'}",
            out / "spec_head.yaml")
    delta: DeltaResult = compute_delta(old, new) if file_changed else DeltaResult(
        unchanged=[k for k, _, _ in iter_operations(new)])
    all_ops = sorted(k for k, _, _ in iter_operations(new))
    log.add("Análisis delta", f"{len(delta.added)} nuevas, {len(delta.modified)} modificadas, "
            f"{len(delta.removed)} eliminadas, {len(delta.unchanged)} sin cambios. Nuevas: "
            f"{', '.join(map(str, delta.added)) or '—'}. Modificadas: {', '.join(map(str, delta.modified)) or '—'}")

    result: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": s.mode, "run_id": run_id or s.mode, "model": s.model if flags["llm"] else None,
        "provider": s.provider if flags["llm"] else None,
        "spec_file_changed": file_changed, "delta": delta.to_dict(),
        "operations_total": len(all_ops),
    }

    # Atajo del análisis delta: sin cambios en el contrato no se gasta ningún token.
    if flags["delta"] and not delta.targets:
        log.add("Fin", "el contrato no cambió: no se generan pruebas (0 tokens)")
        result.update(_empty_metrics(), status="no_contract_changes", steps=log.steps,
                      duration_s=round(time.perf_counter() - t0, 3))
        _write_reports(out, result)
        return result

    # Verificación previa: si la API no responde, no se gasta ni un token del LLM.
    if not api_is_up(s.base_url):
        log.add("Verificación de la API", f"SIN RESPUESTA en {s.base_url}: se detiene sin llamar al LLM")
        result.update(_empty_metrics(), status="api_unreachable", steps=log.steps,
                      error=f"No hay ninguna API respondiendo en {s.base_url}. "
                            "¿Está corriendo el servidor (uvicorn / docker)?",
                      duration_s=round(time.perf_counter() - t0, 3))
        _write_reports(out, result)
        return result

    cov_targets: list[OperationKey] = (
        delta.targets if (s.coverage_scope == "delta" and delta.targets) else all_ops)
    scope_ops = delta.targets if flags["delta"] else all_ops
    spec_for_tests = build_subspec(new, scope_ops) if flags["delta"] else new
    spec_text = dump_spec(spec_for_tests, s.spec_format)
    full_text = dump_spec(new, s.spec_format)
    (out / "spec_context.yaml").write_text(spec_text, encoding="utf-8")
    log.add("Verificación de la API", f"responde en {s.base_url}")
    log.add("Construcción del contexto",
            (f"sub-especificación con {len(scope_ops)} de {len(all_ops)} operaciones" if flags["delta"]
             else f"especificación completa ({len(all_ops)} operaciones)")
            + f"; {len(spec_text):,} caracteres (completa: {len(full_text):,})", out / "spec_context.yaml")
    result.update({
        "target_operations": [str(k) for k in cov_targets],
        "context_operations": len(scope_ops),
        "spec_context_chars": len(spec_text),
        "spec_full_chars": len(full_text),
        "spec_context_tokens_est": _approx_tokens(spec_text),
        "spec_full_tokens_est": _approx_tokens(full_text),
        "context_reduction": round(1 - len(spec_text) / max(1, len(full_text)), 4),
    })

    if not flags["llm"]:
        result.update(_run_traditional(s, new, delta, out, log))
    else:
        result.update(_run_llm(s, flags, delta, spec_text, out, log))

    cov = compute_coverage(new, cov_targets, Path(result.pop("_http_log")), s.base_url)
    cov_all = compute_coverage(new, all_ops, out / "http_final.jsonl", s.base_url)
    result["coverage"] = cov.to_dict()
    result["http_coverage"] = cov.to_dict()["http_coverage"]
    result["http_coverage_all_ops"] = round(cov_all.ratio, 4)
    log.add("Cálculo de cobertura HTTP",
            f"{cov.covered_pairs}/{cov.documented_pairs} pares (operación, código) cubiertos = {cov.ratio:.1%}; "
            f"{cov.total_requests} peticiones registradas", out / "http_final.jsonl")
    result["duration_s"] = round(time.perf_counter() - t0, 3)
    result["status"] = result.get("status", "ok")
    log.add("Fin", f"estado={result['status']}; tasa ejecutable={result.get('executable_rate')}; "
            f"tokens={result.get('total_tokens', 0)}; duración={result['duration_s']} s", out / "report.json")
    result["steps"] = log.steps
    _write_reports(out, result)
    return result


def api_is_up(base_url: str, timeout: float = 5.0) -> bool:
    """Cualquier respuesta HTTP (incluso 404) cuenta como 'arriba'; solo falla si no hay conexión."""
    try:
        requests.get(base_url, timeout=timeout)
        return True
    except requests.RequestException:
        return False


def _empty_metrics() -> dict[str, Any]:
    return {
        "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
        "generation_tokens": 0, "repair_tokens": 0, "cost_usd": 0.0, "llm_latency_s": 0.0,
        "generated_tests": 0, "executable_tests": 0, "executable_rate": None,
        "passed": 0, "assertion_failures": 0, "runtime_errors": 0, "connection_errors": 0,
        "heal_iterations": 0, "http_coverage": None,
    }


def _run_metrics(run, total: int) -> dict[str, Any]:
    return {
        "generated_tests": total,
        "executable_tests": run.executed,
        "executable_rate": round(run.executed / total, 4) if total else 0.0,
        "passed": run.count("passed"),
        "assertion_failures": run.count("assertion"),
        "runtime_errors": run.count("runtime_error") + run.count("setup_error"),
        "connection_errors": run.count("connection_error"),
        "skipped": run.count("skipped"),
        "collection_error": bool(run.collection_error),
        "pytest_exit_code": run.exit_code,
        "pytest_duration_s": round(run.duration_s, 3),
        "test_cases": [{"test": c.nodeid, "outcome": c.outcome, "message": c.message[:500]}
                       for c in run.cases],
        "possible_regressions": [
            {"test": c.nodeid, "message": c.message[:300]} for c in run.cases if c.outcome == "assertion"
        ],
    }


def _run_traditional(s: Settings, new: dict, delta: DeltaResult, out: Path, log: StepLog) -> dict[str, Any]:
    ops = delta.targets if (s.traditional_scope == "delta" and delta.targets) else None
    spec = build_subspec(new, ops) if ops else new
    spec_file = out / "spec_for_schemathesis.yaml"
    spec_file.write_text(dump_spec(spec), encoding="utf-8")
    test_file = write_schemathesis_test(spec_file, out, s.schemathesis_examples)
    log.add("Generación de casos (Schemathesis, sin IA)",
            f"{len(ops) if ops else 'todas las'} operaciones; {s.schemathesis_examples} ejemplos por operación, "
            "datos válidos e inválidos", test_file)
    http_log = out / "http_final.jsonl"
    http_log.unlink(missing_ok=True)
    r = run_pytest(test_file, out, s.base_url, http_log, timeout_per_test=max(s.pytest_timeout, 300))
    log.add("Ejecución de pruebas (Pytest)", run_summary(r), http_log)
    total = len(r.cases) if r.cases else 1
    m = _empty_metrics()
    m.update(_run_metrics(r, total))
    m["_http_log"] = str(http_log)
    return m


def _run_llm(s: Settings, flags: dict, delta: DeltaResult, spec_text: str, out: Path,
             log: StepLog) -> dict[str, Any]:
    client = make_client(s.provider, s.model, **_client_kwargs(s))
    ledger = Ledger(s.price_input_per_mtok, s.price_output_per_mtok)
    if flags["delta"]:
        focus = prompts.FOCUS_DELTA
    elif s.full_focus_changed and delta.targets:
        focus = prompts.FOCUS_FULL_CHANGED.format(ops=", ".join(map(str, delta.targets)))
    else:
        focus = prompts.FOCUS_FULL
    focus += environment_note(s)
    max_iter = s.max_heal_iterations if flags["heal"] else 0
    hr = generate_and_heal(client, ledger, spec_text, focus, out, s.base_url,
                           max_iterations=max_iter, policy=s.heal_policy,
                           pytest_timeout=s.pytest_timeout, repair_mode=s.repair_mode, log=log)
    m = _empty_metrics()
    m.update(ledger.summary())
    m.update(_run_metrics(hr.final_run, hr.generated_tests))
    first = hr.iterations[0] if hr.iterations else None
    m.update({
        "heal_iterations": sum(1 for it in hr.iterations if it.action.startswith("repair")),
        "repair_mode": s.repair_mode,
        "heal_stop_reason": hr.stopped_reason,
        "executable_rate_before_heal": round(first.executable / first.total, 4) if first and first.total else 0.0,
        "iterations": [asdict(it) for it in hr.iterations],
        "llm_calls_detail": [asdict(c) for c in ledger.calls],
        "static_ok": static_check(hr.final_code).ok,
    })
    if hr.stopped_reason == "api_unreachable":
        m["status"] = "api_unreachable"
    m["_http_log"] = str(hr.final_http_log)
    return m


def environment_note(s: Settings) -> str:
    """Contexto del entorno de pruebas, idéntico para B y C (y sus ablaciones)."""
    note = ""
    if os.environ.get("DELTAHEAL_AUTH_HEADER"):
        note += ("\nEntorno: la fixture `api` YA está autenticada (incluye el header de autorización); "
                 "no hagas login para usarla. Para probar respuestas sin autenticación (401/403) crea una "
                 "sesión sin credenciales: `requests.get(base_url + ruta)`, usando la fixture `base_url`.")
    if s.context_note:
        note += "\nDatos del entorno de pruebas: " + s.context_note.strip()
    return note


def _client_kwargs(s: Settings) -> dict[str, Any]:
    if s.provider == "mock":
        return {"inject_error": bool(s.extra.get("mock_inject_error", True))}
    kw: dict[str, Any] = {"temperature": s.temperature, "max_tokens": s.max_tokens}
    if s.llm_base_url:
        kw["base_url"] = s.llm_base_url
    if s.provider != "anthropic" and s.seed is not None:
        kw["seed"] = s.seed
    if s.provider != "anthropic" and s.llm_rpm is not None:
        kw["rpm"] = s.llm_rpm
    if s.provider != "anthropic" and s.reasoning_effort is not None:
        kw["reasoning_effort"] = s.reasoning_effort
    return kw


# --------------------------------------------------------------------------- #
# Reportes
# --------------------------------------------------------------------------- #

def _write_reports(out: Path, r: dict[str, Any]) -> None:
    (out / "report.json").write_text(json.dumps(r, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(r), encoding="utf-8")


def _pct(x: Any) -> str:
    return "—" if x is None else f"{100 * float(x):.1f}%"


def render_markdown(r: dict[str, Any]) -> str:
    d = r.get("delta", {})
    lines = [f"## 🧪 DeltaHeal — reporte de regresión (`{r['mode']}`)", ""]
    if r.get("status") == "api_unreachable" and r.get("error"):
        lines += [f"❌ {r['error']} No se llamó al LLM (0 tokens)."]
        return "\n".join(lines) + "\n"
    if r.get("status") == "no_contract_changes":
        lines += ["El contrato OpenAPI no cambió respecto a la rama base: no se generaron pruebas (0 tokens)."]
        return "\n".join(lines) + "\n"
    lines += [
        "| Métrica | Valor |", "|---|---|",
        f"| Operaciones nuevas / modificadas / eliminadas | {len(d.get('added', []))} / "
        f"{len(d.get('modified', []))} / {len(d.get('removed', []))} |",
        f"| Reducción de contexto enviado al LLM | "
        f"{_pct(r.get('context_reduction')) if r.get('model') else 'n/a (sin LLM)'} |",
        f"| Tests generados | {r.get('generated_tests')} |",
        f"| Tasa de tests ejecutables | {_pct(r.get('executable_rate'))}"
        + (f" (antes de reparar: {_pct(r.get('executable_rate_before_heal'))})"
           if r.get("executable_rate_before_heal") is not None else "") + " |",
        f"| Pasan / fallas de aserción / errores | {r.get('passed')} / {r.get('assertion_failures')} / "
        f"{r.get('runtime_errors')} |",
        f"| Cobertura de respuestas HTTP (ops objetivo) | {_pct(r.get('http_coverage'))} |",
        f"| Iteraciones de self-healing | {r.get('heal_iterations', 0)} |",
        f"| Tokens (entrada + salida) | {r.get('prompt_tokens', 0)} + {r.get('completion_tokens', 0)} "
        f"= {r.get('total_tokens', 0)} |",
        f"| Costo estimado | ${r.get('cost_usd', 0):.4f} |",
        f"| Respuestas del LLM cortadas por límite de salida | {r.get('llm_truncated_calls', 0)} |",
        f"| Duración total | {r.get('duration_s')} s |",
        "",
    ]
    if d.get("added") or d.get("modified"):
        lines += ["<details><summary>Operaciones analizadas</summary>", ""]
        lines += [f"- 🆕 `{o}`" for o in d.get("added", [])]
        lines += [f"- ✏️ `{o}`" for o in d.get("modified", [])]
        lines += [f"- 🗑️ `{o}`" for o in d.get("removed", [])]
        lines += ["", "</details>", ""]
    if r.get("collection_error"):
        lines += ["> ❌ El archivo de pruebas final no se pudo colectar en Pytest (ver artefactos `junit_*.xml`).", ""]
    regs = r.get("possible_regressions") or []
    if regs:
        lines += ["### ⚠️ Posibles regresiones (fallas de aserción)", ""]
        lines += [f"- `{x['test']}`: {x['message'][:200]}" for x in regs[:30]]
        lines.append("")
    undoc = (r.get("coverage") or {}).get("undocumented_observed") or {}
    if undoc:
        lines += ["### Códigos HTTP observados no documentados en el contrato", ""]
        lines += [f"- `{k}`: {', '.join(map(str, v))}" for k, v in undoc.items()]
    return "\n".join(lines) + "\n"
