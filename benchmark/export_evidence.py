"""Exporta la evidencia del experimento a un libro Excel.

    python benchmark/export_evidence.py                                   # usa benchmark/results
    python benchmark/export_evidence.py benchmark/results evidencia.xlsx

Hojas:
  Leeme            qué contiene el libro y cómo se generó
  Resumen          promedios por configuración (fórmulas sobre la hoja Corridas)
  Corridas         una fila por corrida (API × configuración × repetición)
  Llamadas_LLM     cada llamada al LLM: fase, tokens, latencia, si se cortó, archivos de evidencia
  Prompts          texto EXACTO del prompt enviado y de la respuesta recibida
  Casos_de_prueba  resultado final de cada test generado
  Cobertura        códigos HTTP documentados / observados / cubiertos por operación
  Registro_manual  plantilla para registrar ejecuciones hechas por una persona (opcional)

Todo sale de los archivos que el prototipo guarda en cada corrida (report.json,
llm_calls/*.txt, test_generated.py, junit_*.xml, http_final.jsonl), así que cada fila
puede rastrearse hasta su archivo de origen.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
FONT = "Arial"
HEAD_FILL = PatternFill("solid", start_color="1F3864")
INPUT_FILL = PatternFill("solid", start_color="FFF2CC")
THIN = Side(style="thin", color="BFBFBF")
CELL_LIMIT = 32000  # Excel admite 32.767 caracteres por celda

CONFIG_DESC = {
    "traditional": "A · Herramienta tradicional sin IA (Schemathesis)",
    "llm_full": "B · LLM básico con OpenAPI completa, sin reparación",
    "deltaheal": "C · Prototipo: análisis delta + self-healing",
    "delta_only": "Ablación: análisis delta sin self-healing",
    "full_heal": "Ablación: OpenAPI completa con self-healing",
}
ORDER = list(CONFIG_DESC)


def _style_header(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name=FONT, bold=True, color="FFFFFF")
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def _table(ws, headers: list[str], rows: list[list], widths: list[int] | None = None,
           start_row: int = 1) -> None:
    for j, h in enumerate(headers, 1):
        ws.cell(row=start_row, column=j, value=h)
    _style_header(ws, start_row, len(headers))
    for i, r in enumerate(rows, start_row + 1):
        for j, v in enumerate(r, 1):
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = Font(name=FONT, size=10)
            cell.alignment = Alignment(vertical="top", wrap_text=isinstance(v, str) and len(v) > 60)
    for j in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths[j - 1] if widths else 16)
    if rows:
        ws.auto_filter.ref = f"A{start_row}:{get_column_letter(len(headers))}{start_row + len(rows)}"


def _cut(text: str) -> str:
    return text if len(text) <= CELL_LIMIT else text[:CELL_LIMIT] + "\n…[recortado; ver archivo de evidencia]"


def load_runs(results_dir: Path) -> list[dict]:
    csv_path = results_dir / "results.csv"
    if not csv_path.exists():
        raise SystemExit(f"No existe {csv_path}. Ejecuta primero benchmark/run_benchmark.py")
    runs = []
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            run_dir = results_dir / row["api"] / f"{row['config']}_r{row['rep']}"
            rep_path = run_dir / "report.json"
            report = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.exists() else {}
            runs.append({"row": row, "report": report, "dir": run_dir})
    runs.sort(key=lambda r: (r["row"]["api"], ORDER.index(r["row"]["config"])
                             if r["row"]["config"] in ORDER else 99, int(r["row"]["rep"])))
    return runs


def _num(v):
    if v in (None, ""):
        return None
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v


def build(results_dir: Path, out: Path) -> Path:
    runs = load_runs(results_dir)
    wb = Workbook()

    # ---------------- Leeme ----------------
    ws = wb.active
    ws.title = "Leeme"
    model = next((r["report"].get("model") for r in runs if r["report"].get("model")), "—")
    info = [
        ("Evidencia del experimento DeltaHeal", None),
        ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Carpeta de resultados", str(results_dir)),
        ("Corridas registradas", len(runs)),
        ("Modelo LLM", model),
        ("", None),
        ("Configuraciones", None),
        *[(k, v) for k, v in CONFIG_DESC.items()],
        ("", None),
        ("Cómo se obtuvo cada dato", None),
        ("Corridas", "results.csv + report.json de cada corrida (benchmark/results/<api>/<config>_r<rep>/)"),
        ("Llamadas_LLM / Prompts", "llm_calls/NN_<fase>_prompt.txt y _response.txt: texto exacto enviado y recibido"),
        ("Casos_de_prueba", "Resultado de Pytest (JUnit XML) de la versión final del archivo de pruebas"),
        ("Cobertura", "Tráfico HTTP real registrado por el plugin (http_final.jsonl) vs. códigos del contrato"),
        ("Tokens", "Reportados por el proveedor del LLM (incluyen tokens de razonamiento)"),
        ("Costo (USD)", "Equivalente a precio de lista de la capa de pago; con nivel gratuito el gasto real es $0"),
        ("Tasa ejecutable", "Tests que corren hasta el final (pasan o fallan por aserción) / tests generados"),
        ("Cobertura HTTP", "Pares (operación, código) documentados y observados / documentados, en ops del delta"),
        ("", None),
        ("Registro_manual", "Plantilla opcional para ejecuciones hechas por una persona. Celdas amarillas = editar."),
    ]
    for i, (k, v) in enumerate(info, 1):
        ws.cell(row=i, column=1, value=k).font = Font(name=FONT, bold=v is None and k != "", size=12 if i == 1 else 10)
        if v is not None:
            ws.cell(row=i, column=2, value=v).font = Font(name=FONT, size=10)
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 100

    # ---------------- Corridas ----------------
    wc = wb.create_sheet("Corridas")
    cols = [
        ("Fecha y hora", 19), ("API", 14), ("Config.", 13), ("Descripción", 38), ("Rep.", 6),
        ("Estado", 11), ("Modelo", 18), ("Tests generados", 10), ("Tests ejecutables", 10),
        ("Tasa ejecutable", 10), ("Tasa antes de reparar", 10), ("Pasan", 8), ("Fallas aserción", 9),
        ("Errores código", 9), ("Pares cubiertos", 9), ("Pares documentados", 10), ("Cobertura HTTP", 10),
        ("Tokens entrada", 10), ("Tokens salida", 10), ("Tokens totales", 10), ("Tokens generación", 10),
        ("Tokens reparación", 10), ("Costo equiv. (USD)", 11), ("Llamadas LLM", 8), ("Iteraciones reparación", 9),
        ("Respuestas cortadas", 9), ("Reducción contexto", 10), ("Duración (s)", 10), ("API sana al terminar", 14), ("Carpeta de evidencia", 40),
    ]
    headers = [c[0] for c in cols]
    L = {h: get_column_letter(i) for i, h in enumerate(headers, 1)}
    rows = []
    for n, r in enumerate(runs, 2):
        row, rep = r["row"], r["report"]
        rows.append([
            rep.get("timestamp", ""), row["api"], row["config"], CONFIG_DESC.get(row["config"], ""),
            _num(row["rep"]), row["status"], rep.get("model") or "— (sin LLM)",
            _num(row["generated_tests"]), _num(row["executable_tests"]),
            f'=IFERROR({L["Tests ejecutables"]}{n}/{L["Tests generados"]}{n},"")',
            _num(row.get("executable_rate_before_heal")) if row["config"] not in ("traditional",) else None,
            _num(row["passed"]), _num(row["assertion_failures"]), _num(row["runtime_errors"]),
            _num(row["covered_pairs"]), _num(row["documented_pairs"]),
            f'=IFERROR({L["Pares cubiertos"]}{n}/{L["Pares documentados"]}{n},"")',
            _num(row["prompt_tokens"]) or 0, _num(row["completion_tokens"]) or 0,
            f'={L["Tokens entrada"]}{n}+{L["Tokens salida"]}{n}',
            _num(row["generation_tokens"]) or 0, _num(row["repair_tokens"]) or 0,
            _num(row["cost_usd"]) or 0, _num(row["llm_calls"]) or 0, _num(row["heal_iterations"]) or 0,
            _num(row.get("llm_truncated_calls")) or 0, _num(row["context_reduction"]),
            _num(row["duration_s"]), row.get("api_smoke_after") or "—", str(r["dir"].relative_to(ROOT)) if r["dir"].is_relative_to(ROOT) else str(r["dir"]),
        ])
    _table(wc, headers, rows, [c[1] for c in cols])
    last = len(rows) + 1
    pct = {"Tasa ejecutable", "Tasa antes de reparar", "Cobertura HTTP", "Reducción contexto"}
    for h in headers:
        for i in range(2, last + 1):
            cell = wc[f"{L[h]}{i}"]
            if h in pct:
                cell.number_format = "0.0%"
            elif h == "Costo equiv. (USD)":
                cell.number_format = "$0.0000"
            elif h.startswith("Tokens"):
                cell.number_format = "#,##0"
    wc[f"{L['Costo equiv. (USD)']}1"].comment = Comment(
        "Calculado con el precio de lista configurado en benchmark.yaml (price_input/output_per_mtok). "
        "Con el nivel gratuito del proveedor el gasto real es $0.", "DeltaHeal")

    # ---------------- Resumen ----------------
    wr = wb.create_sheet("Resumen", 1)
    configs = [c for c in ORDER if any(r["row"]["config"] == c for r in runs)]
    metrics = [("Tasa ejecutable", "0.0%"), ("Cobertura HTTP", "0.0%"), ("Tokens totales", "#,##0"),
               ("Tokens generación", "#,##0"), ("Tokens reparación", "#,##0"),
               ("Costo equiv. (USD)", "$0.0000"), ("Duración (s)", "0.0")]
    wr["A1"] = "Promedios por configuración (solo corridas con Estado = ok). Se recalculan desde la hoja Corridas."
    wr["A1"].font = Font(name=FONT, bold=True)
    hdr = ["Config.", "Descripción", "Corridas"] + [f"Prom. {m}" for m, _ in metrics]
    for j, h in enumerate(hdr, 1):
        wr.cell(row=3, column=j, value=h)
    _style_header(wr, 3, len(hdr))
    rng = lambda h: f"Corridas!${L[h]}$2:${L[h]}${last}"  # noqa: E731
    for i, c in enumerate(configs, 4):
        wr.cell(row=i, column=1, value=c)
        wr.cell(row=i, column=2, value=CONFIG_DESC[c])
        wr.cell(row=i, column=3, value=f'=COUNTIFS({rng("Config.")},$A{i},{rng("Estado")},"ok")')
        for j, (m, fmt) in enumerate(metrics, 4):
            cell = wr.cell(row=i, column=j,
                           value=f'=IFERROR(AVERAGEIFS({rng(m)},{rng("Config.")},$A{i},{rng("Estado")},"ok"),"")')
            cell.number_format = fmt
        for j in range(1, len(hdr) + 1):
            wr.cell(row=i, column=j).font = Font(name=FONT, size=10)
    r0 = 4 + len(configs) + 1
    if "llm_full" in configs and "deltaheal" in configs:
        rb, rc = 4 + configs.index("llm_full"), 4 + configs.index("deltaheal")
        tok_col = get_column_letter(4 + [m for m, _ in metrics].index("Tokens totales"))
        wr.cell(row=r0, column=1, value="Reducción de tokens C vs. B").font = Font(name=FONT, bold=True)
        cell = wr.cell(row=r0, column=3, value=f'=IFERROR(1-{tok_col}{rc}/{tok_col}{rb},"")')
        cell.number_format = "0.0%"
        cell.font = Font(name=FONT, bold=True)
    wr.column_dimensions["A"].width = 14
    wr.column_dimensions["B"].width = 46
    for j in range(3, len(hdr) + 1):
        wr.column_dimensions[get_column_letter(j)].width = 14

    # ---------------- Llamadas_LLM / Prompts ----------------
    wl = wb.create_sheet("Llamadas_LLM")
    wp = wb.create_sheet("Prompts")
    lrows, prows = [], []
    for r in runs:
        row, rep = r["row"], r["report"]
        calls_dir = r["dir"] / "llm_calls"
        for k, c in enumerate(rep.get("llm_calls_detail") or [], 1):
            pf = calls_dir / f"{k:02d}_{c['phase']}_prompt.txt"
            rf = calls_dir / f"{k:02d}_{c['phase']}_response.txt"
            rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)  # noqa: E731
            lrows.append([row["api"], row["config"], _num(row["rep"]), k, c["phase"], c["prompt_tokens"],
                          c["completion_tokens"], c.get("reasoning_tokens", 0), round(c["latency_s"], 2),
                          "sí" if c.get("truncated") else "no", round(c["cost_usd"], 6),
                          rel(pf) if pf.exists() else "", rel(rf) if rf.exists() else ""])
            prows.append([row["api"], row["config"], _num(row["rep"]), k, c["phase"],
                          _cut(pf.read_text(encoding="utf-8")) if pf.exists() else "(no guardado)",
                          _cut(rf.read_text(encoding="utf-8")) if rf.exists() else "(no guardado)"])
    _table(wl, ["API", "Config.", "Rep.", "Nº llamada", "Fase", "Tokens entrada", "Tokens salida",
                "Tokens razonamiento", "Latencia (s)", "¿Cortada?", "Costo equiv. (USD)",
                "Archivo prompt", "Archivo respuesta"], lrows,
           [14, 13, 6, 9, 10, 11, 11, 12, 10, 9, 12, 55, 55])
    _table(wp, ["API", "Config.", "Rep.", "Nº llamada", "Fase", "Prompt enviado (texto exacto)",
                "Respuesta recibida (texto exacto)"], prows, [14, 13, 6, 9, 10, 90, 90])
    for row_cells in wp.iter_rows(min_row=2):
        for cell in row_cells[5:7]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    # ---------------- Casos_de_prueba ----------------
    wt = wb.create_sheet("Casos_de_prueba")
    names = {"passed": "Pasa", "assertion": "Falla de aserción", "runtime_error": "Error de código",
             "setup_error": "Error de fixture", "connection_error": "Error de conexión", "skipped": "Omitido"}
    trows = [[r["row"]["api"], r["row"]["config"], _num(r["row"]["rep"]), t["test"],
              names.get(t["outcome"], t["outcome"]), t.get("message", "")]
             for r in runs for t in (r["report"].get("test_cases") or [])]
    _table(wt, ["API", "Config.", "Rep.", "Test", "Resultado", "Mensaje"], trows, [14, 13, 6, 60, 18, 80])

    # ---------------- Cobertura ----------------
    wv = wb.create_sheet("Cobertura")
    vrows = []
    for r in runs:
        for op, v in ((r["report"].get("coverage") or {}).get("per_operation") or {}).items():
            vrows.append([r["row"]["api"], r["row"]["config"], _num(r["row"]["rep"]), op,
                          ", ".join(map(str, v["documented"])), ", ".join(map(str, v["observed"])),
                          ", ".join(map(str, v["covered"])), len(v["covered"]), len(v["documented"])])
    _table(wv, ["API", "Config.", "Rep.", "Operación", "Códigos documentados", "Códigos observados",
                "Códigos cubiertos", "Nº cubiertos", "Nº documentados"], vrows, [14, 13, 6, 30, 18, 18, 18, 10, 12])

    # ---------------- Registro_manual ----------------
    wm = wb.create_sheet("Registro_manual")
    legend = [
        "Plantilla OPCIONAL para registrar una ejecución hecha por una persona (p. ej. si tu asesor pide",
        "contrastar con pruebas manuales en Postman o con un LLM usado a mano en el chat web).",
        "Celdas amarillas = completar. La fila 6 es un EJEMPLO: reemplázala. Una fila por ejecución.",
    ]
    for i, t in enumerate(legend, 1):
        wm.cell(row=i, column=1, value=t).font = Font(name=FONT, italic=True, size=10)
    mh = ["Fecha", "Ejecutor", "API", "Configuración", "Rep.", "Herramienta", "Prompt usado (texto exacto)",
          "Tests escritos/generados", "Tests ejecutables", "Pasan", "Fallan", "Códigos HTTP observados",
          "Tiempo empleado (min)", "Tokens (si la herramienta los muestra)", "Evidencia (captura / archivo)",
          "Observaciones", "Tasa ejecutable"]
    for j, h in enumerate(mh, 1):
        wm.cell(row=5, column=j, value=h)
    _style_header(wm, 5, len(mh))
    example = ["2026-11-10", "M. Ezcurra", "petstore3", "B manual (chat web)", 1, "Gemini (chat web)",
               "Genera pruebas Pytest para esta especificación OpenAPI: <pegar spec>", 20, 18, 15, 3,
               "200, 400, 404", 25, "", "capturas/b_manual_r1.png", "Ejemplo: reemplazar"]
    for r_i in range(6, 26):
        for j in range(1, len(mh)):
            cell = wm.cell(row=r_i, column=j, value=example[j - 1] if r_i == 6 else None)
            cell.fill = INPUT_FILL
            cell.font = Font(name=FONT, size=10, color="0000FF")
            cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
        c = wm.cell(row=r_i, column=len(mh), value=f'=IFERROR(I{r_i}/H{r_i},"")')
        c.number_format = "0.0%"
        c.font = Font(name=FONT, size=10)
    widths = [11, 14, 12, 18, 6, 16, 50, 10, 10, 8, 8, 18, 10, 12, 26, 30, 10]
    for j, w in enumerate(widths, 1):
        wm.column_dimensions[get_column_letter(j)].width = w

    for sheet in wb.worksheets:
        sheet.sheet_view.zoomScale = 90
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def main() -> int:
    results_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "benchmark" / "results"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else results_dir / "evidencia_experimento.xlsx"
    path = build(results_dir.resolve(), out.resolve())
    print(f"Evidencia exportada: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
