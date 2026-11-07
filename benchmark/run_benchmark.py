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
    "duration_s", "llm_latency_s", "pytest_duration_s", "api_smoke_after",
]


def build_base_spec(head: dict, scenario: dict) -> dict:
    """Versión 'anterior' del contrato. Cada regla deshace un cambio que el 'commit' introdujo:

      remove_operations  ["MÉTODO /ruta"]          -> el commit AGREGÓ esas operaciones
      remove_properties  {Esquema: [campos]}        -> el commit AGREGÓ esos campos
      remove_required    {Esquema: [campos]}        -> el commit volvió OBLIGATORIOS esos campos
      remove_parameters  {"MÉTODO /ruta": [nombres]} -> el commit AGREGÓ esos parámetros
      remove_responses   {"MÉTODO /ruta": [códigos]} -> el commit DOCUMENTÓ esas respuestas HTTP
    """
    base = copy.deepcopy(head)
    schemas_root = "#/components/schemas" if "components" in base else "#/definitions"

    def op_of(spec: dict, key: str) -> dict | None:
        method, path = key.split(" ", 1)
        return (spec.get("paths", {}).get(path) or {}).get(method.lower())

    for op in scenario.get("remove_operations", []) or []:
        method, path = op.split(" ", 1)
        item = base.get("paths", {}).get(path)
        if item:
            item.pop(method.lower(), None)
            if not any(m in item for m in HTTP_METHODS):
                base["paths"].pop(path)
    for schema, props in (scenario.get("remove_properties") or {}).items():
        try:
            node = resolve_pointer(base, f"{schemas_root}/{schema}")
        except (KeyError, ValueError):
            continue
        for p in props:
            (node.get("properties") or {}).pop(p, None)
            if p in (node.get("required") or []):
                node["required"].remove(p)
    for schema, props in (scenario.get("remove_required") or {}).items():
        try:
            node = resolve_pointer(base, f"{schemas_root}/{schema}")
        except (KeyError, ValueError):
            continue
        node["required"] = [r for r in node.get("required", []) if r not in props]
        if not node["required"]:
            node.pop("required")
    for key, names in (scenario.get("remove_parameters") or {}).items():
        op = op_of(base, key)
        if op and op.get("parameters"):
            op["parameters"] = [p for p in op["parameters"] if p.get("name") not in names]
    for key, codes in (scenario.get("remove_responses") or {}).items():
        op = op_of(base, key)
        if op:
            for c in codes:
                op.get("responses", {}).pop(str(c), None)
    return base


def sh(cmd: str | list[str] | None, cwd: Path | None = None, log: list | None = None) -> None:
    """Ejecuta uno o varios comandos; los errores no detienen el experimento.
    Si se pasa `log`, registra cada comando y su código de salida (evidencia)."""
    for c in ([cmd] if isinstance(cmd, str) else (cmd or [])):
        if c:
            p = subprocess.run(c, shell=True, check=False, cwd=str(cwd) if cwd else None,
                               capture_output=log is not None, text=True, encoding="utf-8", errors="replace")
            if log is not None:
                tail = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-1:] or [""]
                log.append(_step("Comando de entorno", f"$ {c}  -> código {p.returncode}. {tail[0][:200]}"))


def _step(paso: str, detalle: str) -> dict:
    from datetime import datetime
    return {"hora": datetime.now().isoformat(timespec="seconds"), "paso": paso, "detalle": detalle, "archivo": ""}


def http_calls(base_url: str, calls: list[dict] | None, log: list) -> bool:
    """Peticiones de preparación (p. ej. GET /createdb para poblar la base de datos)."""
    ok = True
    for c in calls or []:
        url = base_url.rstrip("/") + "/" + c["path"].lstrip("/")
        try:
            r = requests.request(c.get("method", "GET"), url, json=c.get("json"), data=c.get("form"), timeout=30)
            log.append(_step("Preparación de datos", f"{c.get('method', 'GET')} {c['path']} -> {r.status_code}"))
            ok &= r.status_code < 400
        except requests.RequestException as e:
            log.append(_step("Preparación de datos", f"{c['path']}: {type(e).__name__}"))
            ok = False
    return ok


def login(base_url: str, auth: dict | None, log: list) -> str | None:
    """Obtiene un token y devuelve el header 'Nombre: valor' para las pruebas de A, B y C."""
    if not auth:
        return None
    lg = auth["login"]
    url = base_url.rstrip("/") + "/" + lg["path"].lstrip("/")
    try:
        r = requests.request(lg.get("method", "POST"), url, json=lg.get("json"), data=lg.get("form"), timeout=30)
        token = r.json().get(auth.get("token_field", "access_token"))
    except Exception as e:  # noqa: BLE001
        log.append(_step("Autenticación", f"login falló: {type(e).__name__}: {e}"))
        return None
    if not token:
        log.append(_step("Autenticación", f"login sin token (HTTP {r.status_code})"))
        return None
    user = (lg.get("json") or lg.get("form") or {}).get("username", "?")
    log.append(_step("Autenticación", f"login como '{user}' -> HTTP {r.status_code}; token obtenido "
                     f"({len(token)} caracteres, no se guarda por seguridad)"))
    return f"{auth.get('header', 'Authorization')}: {auth.get('scheme', 'Bearer')} {token}".replace(": ", ": ", 1)


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


def smoke_ok(base_url: str, checks: list[dict] | None) -> tuple[bool, str]:
    """Prueba de humo: cada check debe devolver el código esperado (por defecto 200).
    Detecta APIs que 'responden' pero están en mal estado (p. ej. 500 por datos corruptos)."""
    for c in checks or []:
        url = base_url.rstrip("/") + "/" + c["path"].lstrip("/")
        try:
            code = requests.request(c.get("method", "GET"), url, timeout=10).status_code
        except requests.RequestException as e:
            return False, f"{c['path']}: {type(e).__name__}"
        if code != int(c.get("expect", 200)):
            return False, f"{c.get('method', 'GET')} {c['path']} -> {code} (esperado {c.get('expect', 200)})"
    return True, "ok"


def prepare_api(api: dict, log: list, attempts: int = 3) -> tuple[bool, str]:
    """Resetea la API, la prepara y espera a que esté sana (health + prueba de humo)."""
    detail = "sin verificar"
    cwd = api_workdir(api)
    for i in range(attempts):
        log.append(_step("Reinicio de la API", f"intento {i + 1}: entorno limpio antes de la corrida"))
        sh(api.get("reset"), cwd, log)
        if not wait_healthy(api.get("health"), int(api.get("startup_timeout", 180))):
            detail = "no responde"
            log.append(_step("Verificación de salud", f"{api.get('health')} no responde"))
            continue
        http_calls(api["base_url"], api.get("setup"), log)
        t0 = time.time()
        while time.time() - t0 < 60:
            ok, detail = smoke_ok(api["base_url"], api.get("smoke"))
            if ok:
                checks = ", ".join(f"{c.get('method', 'GET')} {c['path']}" for c in api.get("smoke") or [])
                log.append(_step("Prueba de humo", f"OK: {checks or 'sin checks'} respondieron lo esperado"))
                return True, "ok"
            time.sleep(3)
        log.append(_step("Prueba de humo", f"FALLÓ: {detail}"))
        print(f"   ⚠ prueba de humo fallida ({detail}); reintentando reset {i + 2}/{attempts}…", flush=True)
    return False, detail


def api_workdir(api: dict) -> Path | None:
    return (ROOT / api["workdir"]) if api.get("workdir") else None


def _append_step_to_report(report: Path, step: dict) -> None:
    if report.exists():
        data = json.loads(report.read_text(encoding="utf-8"))
        data.setdefault("steps", []).append(step)
        report.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _save_run_conditions(cfg: dict, out_dir: Path, cfg_path: str) -> None:
    """Evidencia de las condiciones del experimento (se agrega una entrada por cada ejecución)."""
    import platform
    from datetime import datetime
    from importlib import metadata

    def ver(pkg: str) -> str:
        try:
            return metadata.version(pkg)
        except metadata.PackageNotFoundError:
            return "—"
    apis = {}
    for api in cfg.get("apis", []):
        wd = api_workdir(api)
        commit = "—"
        if wd and (wd / ".git").exists():
            commit = subprocess.run(["git", "-C", str(wd), "rev-parse", "HEAD"], capture_output=True,
                                    text=True).stdout.strip() or "—"
        apis[api["name"]] = {"spec": api.get("spec"), "base_url": api.get("base_url"),
                             "commit_codigo_fuente": commit, "scenario": api.get("scenario")}
    entry = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "archivo_configuracion": str(cfg_path),
        "sistema": f"{platform.system()} {platform.release()} · Python {platform.python_version()}",
        "versiones": {p: ver(p) for p in ("pytest", "schemathesis", "hypothesis", "requests", "pandas", "scipy")},
        "llm": cfg.get("llm"), "orquestador": cfg.get("orchestrator"),
        "configuraciones": cfg.get("configs"), "repeticiones": cfg.get("repetitions"),
        "semilla_orden": cfg.get("random_seed"), "apis": apis,
    }
    path = out_dir / "condiciones_experimento.json"
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    history.append(entry)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


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
    _save_run_conditions(cfg, out_dir, a.config)
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

        if api.get("workdir") and not api_workdir(api).exists():
            print(f"[{api['name']}] falta {api_workdir(api)}: ejecuta primero  python benchmark/setup_apis.py")
            continue
        sh(api.get("start"), api_workdir(api))
        plan = [(c, r) for r in range(1, reps + 1) for c in configs]
        # aleatorización por bloques: cada repetición contiene todas las configs en orden aleatorio
        blocks = [plan[i:i + len(configs)] for i in range(0, len(plan), len(configs))]
        ordered = [x for b in blocks for x in rng.sample(b, len(b))]

        for order, (conf, rep) in enumerate(ordered, 1):
            if (api["name"], conf, rep) in done:
                continue
            prep: list = []
            ok, detail = prepare_api(api, prep)
            auth_header = login(api["base_url"], api.get("auth"), prep) if ok else None
            if ok and api.get("auth") and not auth_header:
                ok, detail = False, "no se pudo iniciar sesión"
            if not ok:
                print(f"[{api['name']}] API en mal estado ({detail}); se omite {conf}#{rep}. "
                      "Vuelve a ejecutar luego: la corrida queda pendiente.")
                continue
            s = Settings.load(
                None,
                spec_path=str(scen_dir / "head.yaml"), base_url=api["base_url"], mode=conf,
                provider=llm.get("provider", "gemini"), model=llm.get("model", "gemini-3.8-flash"),
                llm_rpm=llm.get("rpm"),
                llm_base_url=llm.get("base_url"), temperature=llm.get("temperature", 0.2),
                max_tokens=llm.get("max_tokens", 32000), seed=rep,
                reasoning_effort=llm.get("reasoning_effort"),
                price_input_per_mtok=llm.get("price_input_per_mtok", 0.0),
                price_output_per_mtok=llm.get("price_output_per_mtok", 0.0),
                output_dir=str(out_dir / api["name"]),
                context_note=api.get("context_note", ""),
                **cfg.get("orchestrator", {}),
                **({"mock_inject_error": llm.get("mock_inject_error", True)} if llm.get("provider") == "mock" else {}),
            )
            import os
            if auth_header:
                os.environ["DELTAHEAL_AUTH_HEADER"] = auth_header
            else:
                os.environ.pop("DELTAHEAL_AUTH_HEADER", None)
            print(f"[{api['name']}] {conf} rep={rep} …", flush=True)
            try:
                res = run(s, old_spec_path=str(scen_dir / "base.yaml"), run_id=f"{conf}_r{rep}",
                          prior_steps=prep)
            except QuotaExhaustedError as e:
                print(f"\n⏸  {e}\nLas corridas completadas están guardadas en {csv_path}.")
                try:
                    from export_evidence import build_all
                    for xlsx in build_all(out_dir):
                        print(f"Evidencia parcial en Excel: {xlsx}")
                except Exception:
                    pass
                sh(api.get("stop"), api_workdir(api))
                return 5
            except Exception as e:  # una corrida fallida no detiene el experimento
                res = {"status": f"crash: {type(e).__name__}: {e}"}
            # estado de la API al terminar (los propios tests pueden dejarla en mal estado: se registra)
            res["api_smoke_after"] = smoke_ok(api["base_url"], api.get("smoke"))[1]
            _append_step_to_report(out_dir / api["name"] / f"{conf}_r{rep}" / "report.json",
                                   _step("Estado de la API al terminar", res["api_smoke_after"]))
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
        sh(api.get("stop"), api_workdir(api))

    try:
        from export_evidence import build_all
        print()
        for xlsx in build_all(out_dir):
            print(f"Evidencia en Excel: {xlsx}")
    except Exception as e:  # la exportación nunca debe romper el experimento
        print(f"(no se pudo exportar el Excel de evidencia: {e})")
    print(f"\nResultados: {csv_path}\nAnaliza con: python benchmark/analyze.py {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
