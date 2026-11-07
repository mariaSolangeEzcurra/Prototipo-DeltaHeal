"""Experimento controlado de benchmarking.

    python benchmark/run_benchmark.py -c benchmark/benchmark.yaml
    python benchmark/run_benchmark.py -c benchmark/benchmark.yaml --apis petstore3 --reps 1   # prueba corta

- Construye, por API, el escenario de cambio (spec BASE vs. spec HEAD).
- Ejecuta cada configuración `repetitions` veces, en orden aleatorizado (semilla fija)
  para evitar efectos de orden (caché del proveedor, calentamiento de la API, etc.).
- Resetea el estado de la API antes de cada corrida (comando `reset`).
- Guarda una fila por corrida en results.csv (reanudable: omite corridas ya hechas).
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import random
import subprocess
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from deltaheal.config import Settings, load_dotenv  # noqa: E402
from deltaheal.delta import HTTP_METHODS, resolve_pointer  # noqa: E402
from deltaheal.llm import QuotaExhaustedError  # noqa: E402
from deltaheal.orchestrator import run  # noqa: E402
from deltaheal.spec_io import dump_spec, load_spec_file  # noqa: E402

CSV_FIELDS = [
    "api", "config", "rep", "order", "status", "model",
    "generated_tests", "executable_tests", "executable_rate", "executable_rate_before_heal",
    "passed", "assertion_failures", "runtime_errors", "connection_errors", "collection_error",
    "http_coverage", "http_coverage_all_ops", "documented_pairs", "covered_pairs",
    "prompt_tokens", "completion_tokens", "total_tokens", "generation_tokens", "repair_tokens",
    "cost_usd", "llm_calls", "heal_iterations", "heal_stop_reason",
    "reasoning_tokens", "llm_truncated_calls",
    "spec_context_chars", "spec_full_chars", "context_reduction", "target_ops",
    "duration_s", "llm_latency_s", "pytest_duration_s",
]


def build_base_spec(head: dict, scenario: dict) -> dict:
    """Versión 'anterior' del contrato: se eliminan operaciones/propiedades del escenario."""
    base = copy.deepcopy(head)
    for op in scenario.get("remove_operations", []) or []:
        method, path = op.split(" ", 1)
        item = base.get("paths", {}).get(path)
        if item:
            item.pop(method.lower(), None)
            if not any(m in item for m in HTTP_METHODS):
                base["paths"].pop(path)
    schemas_root = "#/components/schemas" if "components" in base else "#/definitions"
    for schema, props in (scenario.get("remove_properties") or {}).items():
        try:
            node = resolve_pointer(base, f"{schemas_root}/{schema}")
        except (KeyError, ValueError):
            continue
        for p in props:
            (node.get("properties") or {}).pop(p, None)
            if p in (node.get("required") or []):
                node["required"].remove(p)
    return base


def sh(cmd: str | list[str] | None) -> None:
    """Ejecuta uno o varios comandos; los errores no detienen el experimento."""
    for c in ([cmd] if isinstance(cmd, str) else (cmd or [])):
        if c:
            subprocess.run(c, shell=True, check=False)


def wait_healthy(url: str | None, timeout: int = 120) -> bool:
    if not url:
        return True
    t0 = time.time()
    warned = False
    while time.time() - t0 < timeout:
        try:
            if requests.get(url, timeout=5).status_code < 500:
                return True
        except requests.RequestException:
            if not warned:
                print(f"   … esperando que la API responda en {url} (¿está levantada?)", flush=True)
                warned = True
        time.sleep(2)
    return False


def done_runs(csv_path: Path) -> set[tuple[str, str, int]]:
    if not csv_path.exists():
        return set()
    with csv_path.open(encoding="utf-8") as fh:
        # las corridas que fallaron (crash) se vuelven a intentar en la siguiente ejecución
        return {(r["api"], r["config"], int(r["rep"])) for r in csv.DictReader(fh)
                if not (r.get("status") or "").startswith("crash")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default=str(ROOT / "benchmark" / "benchmark.yaml"))
    ap.add_argument("--apis", nargs="*", help="subconjunto de APIs")
    ap.add_argument("--configs", nargs="*", help="subconjunto de configuraciones")
    ap.add_argument("--reps", type=int, help="sobrescribe repetitions")
    ap.add_argument("--provider")
    ap.add_argument("--model")
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    a = ap.parse_args()
    load_dotenv(ROOT / ".env")

    cfg = yaml.safe_load(Path(a.config).read_text(encoding="utf-8"))
    reps = a.reps or cfg.get("repetitions", 5)
    configs = a.configs or cfg["configs"]
    llm = dict(cfg.get("llm", {}))
    if a.provider:
        llm["provider"] = a.provider
    if a.model:
        llm["model"] = a.model
    out_dir = ROOT / cfg.get("output_dir", "benchmark/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "results.csv"
    done = done_runs(csv_path)
    rng = random.Random(cfg.get("random_seed", 0))

    for api in cfg["apis"]:
        if a.apis and api["name"] not in a.apis:
            continue
        spec_path = ROOT / api["spec"]
        if not spec_path.exists():
            print(f"[{api['name']}] spec no encontrada en {spec_path}; se omite.")
            continue
        scen_dir = out_dir / api["name"] / "scenario"
        scen_dir.mkdir(parents=True, exist_ok=True)
        head = load_spec_file(spec_path)
        base = build_base_spec(head, api.get("scenario", {}))
        (scen_dir / "head.yaml").write_text(dump_spec(head), encoding="utf-8")
        (scen_dir / "base.yaml").write_text(dump_spec(base), encoding="utf-8")

        sh(api.get("start"))
        plan = [(c, r) for r in range(1, reps + 1) for c in configs]
        # aleatorización por bloques: cada repetición contiene todas las configs en orden aleatorio
        blocks = [plan[i:i + len(configs)] for i in range(0, len(plan), len(configs))]
        ordered = [x for b in blocks for x in rng.sample(b, len(b))]

        for order, (conf, rep) in enumerate(ordered, 1):
            if (api["name"], conf, rep) in done:
                continue
            sh(api.get("reset"))
            if not wait_healthy(api.get("health")):
                print(f"[{api['name']}] API no saludable; se omite {conf}#{rep}")
                continue
            s = Settings.load(
                None,
                spec_path=str(scen_dir / "head.yaml"), base_url=api["base_url"], mode=conf,
                provider=llm.get("provider", "gemini"), model=llm.get("model", "gemini-2.5-flash"),
                llm_rpm=llm.get("rpm"),
                llm_base_url=llm.get("base_url"), temperature=llm.get("temperature", 0.2),
                max_tokens=llm.get("max_tokens", 32000), seed=rep,
                reasoning_effort=llm.get("reasoning_effort"),
                price_input_per_mtok=llm.get("price_input_per_mtok", 0.0),
                price_output_per_mtok=llm.get("price_output_per_mtok", 0.0),
                output_dir=str(out_dir / api["name"]),
                **cfg.get("orchestrator", {}),
                **({"mock_inject_error": llm.get("mock_inject_error", True)} if llm.get("provider") == "mock" else {}),
            )
            if api.get("auth_header"):
                import os
                os.environ["DELTAHEAL_AUTH_HEADER"] = api["auth_header"]
            print(f"[{api['name']}] {conf} rep={rep} …", flush=True)
            try:
                res = run(s, old_spec_path=str(scen_dir / "base.yaml"), run_id=f"{conf}_r{rep}")
            except QuotaExhaustedError as e:
                print(f"\n⏸  {e}\nLas corridas completadas están guardadas en {csv_path}.")
                try:
                    from export_evidence import build
                    build(out_dir, out_dir / "evidencia_experimento.xlsx")
                    print(f"Evidencia parcial en Excel: {out_dir / 'evidencia_experimento.xlsx'}")
                except Exception:
                    pass
                sh(api.get("stop"))
                return 5
            except Exception as e:  # una corrida fallida no detiene el experimento
                res = {"status": f"crash: {type(e).__name__}: {e}"}
            row = {k: res.get(k) for k in CSV_FIELDS}
            row.update(api=api["name"], config=conf, rep=rep, order=order,
                       documented_pairs=(res.get("coverage") or {}).get("documented_pairs"),
                       covered_pairs=(res.get("coverage") or {}).get("covered_pairs"),
                       target_ops=len(res.get("target_operations") or []))
            new_file = not csv_path.exists()
            with csv_path.open("a", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
                if new_file:
                    w.writeheader()
                w.writerow(row)
            print("   ", json.dumps({k: row[k] for k in ("status", "executable_rate", "http_coverage",
                                                         "total_tokens", "cost_usd")}))
        sh(api.get("stop"))

    try:
        from export_evidence import build
        xlsx = build(out_dir, out_dir / "evidencia_experimento.xlsx")
        print(f"\nEvidencia en Excel: {xlsx}")
    except Exception as e:  # la exportación nunca debe romper el experimento
        print(f"(no se pudo exportar el Excel de evidencia: {e})")
    print(f"\nResultados: {csv_path}\nAnaliza con: python benchmark/analyze.py {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
