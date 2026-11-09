"""Generación + bucle de auto-corrección (self-healing loop).

    generar ─► ejecutar pytest ─► ¿defectos del código de prueba? ──no──► fin
                    ▲                         │ sí (y quedan iteraciones)
                    └──── reparar con LLM ◄───┘   (errores capturados de Pytest)

Política de reparación:
- "errors"  (por defecto): se reparan errores de colección/sintaxis, excepciones
  en tiempo de ejecución y errores de fixtures. Las fallas de ASERCIÓN no se envían
  al LLM porque pueden ser regresiones reales de la API: "curarlas" las ocultaría.
- "all": también se envían fallas de aserción (útil como ablación del experimento).

Salvaguardas:
- Si todos los casos fallan por conexión (API caída) se detiene sin gastar tokens.
- Se conserva la mejor versión (más tests ejecutables); si una reparación empeora
  el archivo, se vuelve a la versión anterior.
- Revisión humana opcional (`reviewer`): antes de cada ejecución una persona puede revisar,
  editar o cancelar las pruebas generadas o reparadas.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import prompts
from .generated_code import extract_code, static_check
from .llm import LLMClient, LLMResponse
from .partial_repair import failing_toplevel_names, merge_patch, split_for_patch
from .progress import progress
from .pytest_runner import RunResult, format_assertions_for_llm, format_errors_for_llm, run_pytest
from .step_log import StepLog, run_summary

# Recibe el archivo de pruebas y el número de iteración; devuelve True para ejecutarlo.
Reviewer = Callable[[Path, int], bool]


@dataclass
class LLMCall:
    phase: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float
    cost_usd: float
    reasoning_tokens: int = 0
    truncated: bool = False


@dataclass
class Ledger:
    price_in_per_mtok: float = 0.0
    price_out_per_mtok: float = 0.0
    calls: list[LLMCall] = field(default_factory=list)

    def add(self, phase: str, r: LLMResponse) -> None:
        cost = (r.prompt_tokens * self.price_in_per_mtok + r.completion_tokens * self.price_out_per_mtok) / 1e6
        self.calls.append(LLMCall(phase, r.prompt_tokens, r.completion_tokens, r.latency_s, cost,
                                  getattr(r, "reasoning_tokens", 0), bool(getattr(r, "truncated", False))))

    def summary(self) -> dict[str, Any]:
        def s(attr: str, phase: str | None = None) -> float:
            return sum(getattr(c, attr) for c in self.calls if phase is None or c.phase == phase)
        return {
            "llm_calls": len(self.calls),
            "prompt_tokens": int(s("prompt_tokens")),
            "completion_tokens": int(s("completion_tokens")),
            "total_tokens": int(s("prompt_tokens") + s("completion_tokens")),
            "generation_tokens": int(s("prompt_tokens", "generate") + s("completion_tokens", "generate")),
            "repair_tokens": int(s("prompt_tokens", "repair") + s("completion_tokens", "repair")),
            "reasoning_tokens": int(s("reasoning_tokens")),
            "llm_truncated_calls": sum(1 for c in self.calls if c.truncated),
            "cost_usd": round(s("cost_usd"), 6),
            "llm_latency_s": round(s("latency_s"), 3),
        }


@dataclass
class Iteration:
    index: int
    executable: int
    total: int
    broken: int
    assertion_failures: int
    collection_error: bool
    action: str


@dataclass
class HealingResult:
    final_code: str
    final_run: RunResult
    final_http_log: Path
    test_file: Path
    generated_tests: int
    iterations: list[Iteration]
    stopped_reason: str
    reviews: list[dict[str, Any]] = field(default_factory=list)


def _save_call(workdir: Path, ledger: Ledger, phase: str, system: str, user: str, resp: LLMResponse) -> None:
    """Evidencia: guarda el prompt exacto enviado y la respuesta cruda de cada llamada al LLM."""
    d = workdir / "llm_calls"
    d.mkdir(exist_ok=True)
    n = len(ledger.calls)
    (d / f"{n:02d}_{phase}_prompt.txt").write_text(
        f"### SYSTEM\n{system}\n\n### USER\n{user}\n", encoding="utf-8")
    (d / f"{n:02d}_{phase}_response.txt").write_text(resp.text, encoding="utf-8")


def _total_tests(run: RunResult, static_count: int) -> int:
    if run.collection_error or not run.cases:
        return max(static_count, len(run.cases))
    return len(run.cases)


def generate_and_heal(client: LLMClient, ledger: Ledger, spec_text: str, focus: str,
                      workdir: Path, base_url: str, max_iterations: int = 3,
                      policy: str = "errors", test_name: str = "test_generated.py",
                      pytest_timeout: int = 60, repair_mode: str = "patch",
                      log: StepLog | None = None, extra_env: dict[str, str] | None = None,
                      reviewer: Reviewer | None = None) -> HealingResult:
    log = log or StepLog(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    test_file = workdir / test_name

    user = prompts.USER_GENERATE.format(spec=spec_text, focus=focus)
    with progress.waiting(f"Esperando a la IA ({client.model}): generación de pruebas"):
        resp = client.complete(prompts.SYSTEM_GENERATE, user)
    ledger.add("generate", resp)
    _save_call(workdir, ledger, "generate", prompts.SYSTEM_GENERATE, user, resp)
    code = extract_code(resp.text)
    log.add("Generación de pruebas con el LLM",
            f"{resp.prompt_tokens:,} tokens de entrada + {resp.completion_tokens:,} de salida; "
            f"{static_check(code).test_count} funciones de test; respuesta cortada: {'sí' if resp.truncated else 'no'}",
            workdir / "llm_calls" / f"{len(ledger.calls):02d}_generate_prompt.txt")

    iterations: list[Iteration] = []
    reviews: list[dict[str, Any]] = []
    best: tuple[int, str, RunResult, Path, int] | None = None
    stopped = "max_iterations"

    for i in range(max_iterations + 1):
        test_file.write_text(code, encoding="utf-8")
        if reviewer is not None:
            approved = reviewer(test_file, i)
            reviewed = test_file.read_text(encoding="utf-8")
            edited = reviewed != code
            reviews.append({"iteration": i, "approved": approved, "edited": edited})
            log.add("Revisión humana",
                    f"iteración {i}: {'aprobada' if approved else 'cancelada'}"
                    + ("; el revisor modificó el archivo" if edited else ""), test_file)
            code = reviewed
            if not approved:
                stopped = "review_cancelled"
                if best is None:  # nada se ejecutó todavía
                    empty_log = workdir / "http_final.jsonl"
                    empty_log.write_text("", encoding="utf-8")
                    return HealingResult(code, RunResult(exit_code=-1, duration_s=0.0), empty_log, test_file,
                                         static_check(code).test_count, iterations, stopped, reviews)
                break
        (workdir / f"{test_file.stem}.iter{i}.py").write_text(code, encoding="utf-8")
        st = static_check(code)
        http_log = workdir / f"http_iter{i}.jsonl"
        http_log.unlink(missing_ok=True)
        with progress.waiting(f"Ejecutando las pruebas contra la API (iteración {i})"):
            run = run_pytest(test_file, workdir, base_url, http_log, timeout_per_test=pytest_timeout,
                             junit_name=f"junit_iter{i}.xml", extra_env=extra_env)
        log.add(f"Ejecución de pruebas (iteración {i})",
                ("" if st.ok else f"código con error de sintaxis: {st.error}; ") + run_summary(run),
                workdir / f"{test_file.stem}.iter{i}.py")
        total = _total_tests(run, st.test_count)
        fails = run.count("assertion")

        if best is None or run.executed > best[0]:
            best = (run.executed, code, run, http_log, total)

        conn = run.count("connection_error")
        if run.cases and conn == len(run.cases):
            iterations.append(Iteration(i, run.executed, total, len(run.broken), fails,
                                        bool(run.collection_error), "stop_api_unreachable"))
            stopped = "api_unreachable"
            log.add("Bucle detenido", "la API no responde: no se gastan tokens reparando")
            break

        needs = (not st.ok) or run.has_code_defects or (policy == "all" and fails > 0)
        if not needs:
            iterations.append(Iteration(i, run.executed, total, len(run.broken), fails,
                                        bool(run.collection_error), "done"))
            stopped = "clean"
            log.add("Bucle finalizado", "no quedan errores en el código de prueba"
                    + (f" ({fails} fallas de aserción se reportan como posibles regresiones, no se reparan)" if fails else ""))
            break
        if i == max_iterations:
            iterations.append(Iteration(i, run.executed, total, len(run.broken), fails,
                                        bool(run.collection_error), "give_up"))
            log.add("Bucle finalizado", f"se alcanzó el máximo de iteraciones ({max_iterations})"
                    if max_iterations else "configuración sin self-healing: el código se ejecuta tal como lo generó el LLM")
            break

        errors = st.error + "\n\n" if not st.ok else ""
        errors += format_errors_for_llm(run)
        if policy == "all" and fails:
            errors += "\n\n# Fallas de aserción (revisar contra la especificación)\n" + format_assertions_for_llm(run)
        parts = None
        if repair_mode == "patch" and st.ok and not run.collection_error:
            parts = split_for_patch(code, failing_toplevel_names(run, include_assertions=policy == "all"))
        if parts:
            header, failing = parts
            repair_user = prompts.USER_REPAIR_PATCH.format(
                iteration=i + 1, max_iter=max_iterations, spec=spec_text,
                header=header, failing=failing, errors=errors)
            with progress.waiting(f"Esperando a la IA ({client.model}): reparación {i + 1}"):
                resp = client.complete(prompts.SYSTEM_REPAIR_PATCH, repair_user)
            ledger.add("repair", resp)
            _save_call(workdir, ledger, "repair", prompts.SYSTEM_REPAIR_PATCH, repair_user, resp)
            try:
                new_code = merge_patch(code, extract_code(resp.text))
                action = "repair_patch"
            except (SyntaxError, ValueError):
                new_code, action = code, "repair_patch_failed"  # siguiente iteración: igual reintenta
                repair_mode = "full"                             # y cambia a reparación completa
        else:
            repair_user = prompts.USER_REPAIR.format(iteration=i + 1, max_iter=max_iterations,
                                                     spec=spec_text, code=code, errors=errors)
            with progress.waiting(f"Esperando a la IA ({client.model}): reparación {i + 1}"):
                resp = client.complete(prompts.SYSTEM_REPAIR, repair_user)
            ledger.add("repair", resp)
            _save_call(workdir, ledger, "repair", prompts.SYSTEM_REPAIR, repair_user, resp)
            new_code, action = extract_code(resp.text), "repair_full"
        iterations.append(Iteration(i, run.executed, total, len(run.broken), fails,
                                    bool(run.collection_error), action))
        log.add(f"Reparación con el LLM (iteración {i + 1})",
                f"modo={'parcial: solo tests que fallaron' if action.startswith('repair_patch') else 'archivo completo'}"
                f"{' (parche inválido, se usará reparación completa)' if action == 'repair_patch_failed' else ''}; "
                f"{len(run.broken)} tests con error enviados; {resp.prompt_tokens:,} + {resp.completion_tokens:,} tokens",
                workdir / "llm_calls" / f"{len(ledger.calls):02d}_repair_prompt.txt")
        code = new_code

    assert best is not None
    executed, best_code, best_run, best_log, best_total = best
    log.add("Selección de la versión final", f"se conserva la versión con más tests ejecutables "
            f"({executed}/{best_total})", test_file)
    if best_code != code or best_log != http_log:
        test_file.write_text(best_code, encoding="utf-8")
    final_log = workdir / "http_final.jsonl"
    shutil.copyfile(best_log, final_log) if best_log.exists() else final_log.write_text("", encoding="utf-8")
    return HealingResult(best_code, best_run, final_log, test_file, best_total, iterations, stopped, reviews)
