"""Reporte de cada corrida: report.json (métricas completas) y report.md (legible).

El report.md es el mismo texto que se publica como comentario en el Pull Request.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_reports(out: Path, r: dict[str, Any]) -> None:
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
