"""Análisis estadístico de results.csv.

    python benchmark/analyze.py benchmark/results/results.csv

Produce en la misma carpeta:
  summary_by_api.csv     media, desviación estándar, mediana por (API, configuración)
  summary_pooled.csv     agregados por configuración (las 3 APIs juntas)
  tests.csv              pruebas de hipótesis por métrica
  analysis.md            reporte legible con las tablas de resultados
  fig_<metrica>.png      diagramas de caja (si matplotlib está disponible)

Métodos (no paramétricos, adecuados para n=5 por celda y distribuciones no normales):
  - Kruskal–Wallis entre configuraciones (por API y agrupado).
  - Comparaciones por pares con Mann–Whitney U (bilateral) + corrección de Holm.
  - Tamaño del efecto: delta de Cliff (|d|<0.147 despreciable, <0.33 pequeño,
    <0.474 mediano, ≥0.474 grande; Romano et al., 2006).
  - Friedman pareando por (API, repetición) cuando hay datos completos.
"""

from __future__ import annotations

import sys
import warnings
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

METRICS = {
    "executable_rate": ("Tasa de pruebas ejecutables", "higher"),
    "http_coverage": ("Cobertura de respuestas HTTP", "higher"),
    "total_tokens": ("Tokens totales", "lower"),
    "cost_usd": ("Costo (USD)", "lower"),
    "duration_s": ("Duración (s)", "lower"),
}
ORDER = ["traditional", "llm_full", "deltaheal", "delta_only", "full_heal"]
LABELS = {"traditional": "A · Tradicional", "llm_full": "B · LLM spec completa",
          "deltaheal": "C · Prototipo (delta+healing)", "delta_only": "Abl. delta sin healing",
          "full_heal": "Abl. completa + healing"}


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    gt = sum((xi > y).sum() for xi in x)
    lt = sum((xi < y).sum() for xi in x)
    return (gt - lt) / (len(x) * len(y))


def magnitude(d: float) -> str:
    a = abs(d)
    if np.isnan(a):
        return "n/a"
    return "despreciable" if a < 0.147 else "pequeño" if a < 0.33 else "mediano" if a < 0.474 else "grande"


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[idx]))
        adj[idx] = running
    return adj.tolist()


def safe_kruskal(groups: list[np.ndarray]) -> tuple[float, float]:
    groups = [g for g in groups if len(g) > 0]
    if len(groups) < 2:
        return float("nan"), float("nan")
    allv = np.concatenate(groups)
    if np.all(allv == allv[0]):
        return 0.0, 1.0
    return tuple(stats.kruskal(*groups))  # type: ignore[return-value]


def safe_mwu(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) == 0 or len(y) == 0:
        return float("nan")
    if np.all(np.concatenate([x, y]) == x[0]):
        return 1.0
    return float(stats.mannwhitneyu(x, y, alternative="two-sided").pvalue)


def main(csv_path: str) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    path = Path(csv_path)
    df = pd.read_csv(path, encoding="utf-8")
    df = df[df["status"].fillna("ok").isin(["ok"])].copy()
    for m in METRICS:
        df[m] = pd.to_numeric(df[m], errors="coerce")
    configs = [c for c in ORDER if c in df["config"].unique()]
    out = path.parent

    agg = {m: ["mean", "std", "median"] for m in METRICS}
    by_api = df.groupby(["api", "config"]).agg(agg).round(4)
    by_api.to_csv(out / "summary_by_api.csv")
    pooled = df.groupby("config").agg(agg).round(4).reindex(configs)
    pooled.to_csv(out / "summary_pooled.csv")

    rows = []
    for metric, (label, _) in METRICS.items():
        for scope, sub in [("pooled", df)] + [(a, g) for a, g in df.groupby("api")]:
            groups = {c: sub.loc[sub["config"] == c, metric].dropna().to_numpy() for c in configs}
            H, p = safe_kruskal(list(groups.values()))
            pairs = list(combinations(configs, 2))
            raw = [safe_mwu(groups[a], groups[b]) for a, b in pairs]
            valid = [x if not np.isnan(x) else 1.0 for x in raw]
            adj = holm(valid) if valid else []
            for (a, b), pr, pa in zip(pairs, raw, adj):
                d = cliffs_delta(groups[a], groups[b])
                rows.append({"metric": metric, "scope": scope, "kruskal_H": H, "kruskal_p": p,
                             "a": a, "b": b, "median_a": np.median(groups[a]) if len(groups[a]) else np.nan,
                             "median_b": np.median(groups[b]) if len(groups[b]) else np.nan,
                             "mwu_p": pr, "mwu_p_holm": pa, "cliffs_delta": d, "effect": magnitude(d)})
    tests = pd.DataFrame(rows)
    tests.to_csv(out / "tests.csv", index=False)

    # Friedman: bloques (api, rep) con todas las configuraciones presentes
    friedman = {}
    for metric in METRICS:
        piv = df.pivot_table(index=["api", "rep"], columns="config", values=metric).dropna()
        if len(piv) >= 2 and piv.shape[1] >= 3:
            vals = [piv[c].to_numpy() for c in piv.columns]
            try:
                friedman[metric] = stats.friedmanchisquare(*vals)
            except ValueError:
                pass

    md = ["# Resultados del experimento", "",
          f"Corridas válidas: **{len(df)}** · APIs: {', '.join(sorted(df['api'].unique()))} · "
          f"Configuraciones: {', '.join(LABELS.get(c, c) for c in configs)}", "",
          "## Resumen agrupado (media ± desviación estándar)", "",
          "| Configuración | " + " | ".join(l for l, _ in METRICS.values()) + " |",
          "|---|" + "---|" * len(METRICS)]
    for c in configs:
        cells = []
        for m in METRICS:
            mu, sd = pooled.loc[c, (m, "mean")], pooled.loc[c, (m, "std")]
            fmt = "{:.1%} ± {:.1%}" if m in ("executable_rate", "http_coverage") else (
                "{:.4f} ± {:.4f}" if m == "cost_usd" else "{:.1f} ± {:.1f}")
            cells.append(fmt.format(mu, 0 if pd.isna(sd) else sd) if not pd.isna(mu) else "—")
        md.append(f"| {LABELS.get(c, c)} | " + " | ".join(cells) + " |")

    if {"llm_full", "deltaheal"} <= set(configs):
        b = df[df.config == "llm_full"]["total_tokens"].mean()
        c_ = df[df.config == "deltaheal"]["total_tokens"].mean()
        if b:
            md += ["", f"**Reducción de tokens C vs. B:** {1 - c_ / b:.1%} "
                       f"(media {c_:.0f} vs. {b:.0f} tokens por corrida)."]
        if "executable_rate_before_heal" in df:
            pre = pd.to_numeric(df[df.config == "deltaheal"]["executable_rate_before_heal"], errors="coerce").mean()
            post = df[df.config == "deltaheal"]["executable_rate"].mean()
            md.append(f"**Efecto del self-healing en C:** tasa ejecutable {pre:.1%} → {post:.1%}.")

    md += ["", "## Pruebas de hipótesis (agrupado)", "",
           "| Métrica | Kruskal–Wallis H (p) | Par | p (Holm) | δ de Cliff | Efecto |", "|---|---|---|---|---|---|"]
    for _, r in tests[tests.scope == "pooled"].iterrows():
        md.append(f"| {METRICS[r.metric][0]} | {r.kruskal_H:.2f} ({r.kruskal_p:.4f}) | {r.a} vs {r.b} | "
                  f"{r.mwu_p_holm:.4f} | {r.cliffs_delta:+.2f} | {r.effect} |")
    if friedman:
        md += ["", "## Friedman (bloques = API × repetición)", ""]
        for m, res in friedman.items():
            md.append(f"- {METRICS[m][0]}: χ² = {res.statistic:.2f}, p = {res.pvalue:.4f}")
    md += ["", "Detalle por API en `tests.csv` y `summary_by_api.csv`.", "",
           "_Nota: con n = 5 por celda la potencia estadística es limitada; reporta tamaños de efecto "
           "junto con los p-valores y evita concluir equivalencia a partir de p > 0.05._"]
    (out / "analysis.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for m, (label, _) in METRICS.items():
            apis = sorted(df["api"].unique())
            fig, axes = plt.subplots(1, len(apis), figsize=(4.2 * len(apis), 3.8), squeeze=False)
            for ax, api in zip(axes[0], apis):
                sub = df[df.api == api]
                data = [sub.loc[sub.config == c, m].dropna() for c in configs]
                ax.boxplot(data, tick_labels=[c.replace("_", "\n") for c in configs])
                ax.set_title(api)
                ax.grid(axis="y", alpha=.3)
            axes[0][0].set_ylabel(label)
            fig.tight_layout()
            fig.savefig(out / f"fig_{m}.png", dpi=150)
            plt.close(fig)
    except Exception as e:  # gráficos opcionales
        print(f"(sin gráficos: {e})")

    print((out / "analysis.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "benchmark/results/results.csv"))
