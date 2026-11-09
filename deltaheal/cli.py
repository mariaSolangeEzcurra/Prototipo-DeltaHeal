"""CLI: `python -m deltaheal <comando>`.

Comandos:
  run    ejecuta el pipeline en una configuración (traditional | llm_full | deltaheal | ...)
  delta  solo muestra el análisis delta (sin LLM, sin API) — útil para depurar.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import MODES, Settings, load_dotenv
from .delta import build_subspec, compute_delta
from .spec_loader import dump_spec, load_spec_at_ref, load_spec_file


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--config", "-c", help="archivo YAML de configuración")
    p.add_argument("--spec", dest="spec_path", help="ruta de la spec OpenAPI dentro del repo")
    p.add_argument("--base-ref", help="ref git base (p. ej. origin/main o el SHA base del PR)")
    p.add_argument("--head-ref", help="ref git head (por defecto: working tree)")
    p.add_argument("--old-spec", help="comparar contra este archivo en lugar de usar git")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="deltaheal", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="ejecutar pipeline")
    _common(r)
    r.add_argument("--mode", choices=list(MODES))
    r.add_argument("--base-url", help="URL base de la API bajo prueba")
    r.add_argument("--provider")
    r.add_argument("--model")
    r.add_argument("--llm-base-url")
    r.add_argument("--max-heal-iterations", type=int)
    r.add_argument("--heal-policy", choices=["errors", "all"])
    r.add_argument("--output-dir")
    r.add_argument("--run-id")
    r.add_argument("--fail-on", choices=["regression", "any", "never"])
    r.add_argument("--json", action="store_true", help="imprimir el reporte JSON completo")

    m = sub.add_parser("models", help="listar los modelos disponibles para la clave configurada")
    m.add_argument("--provider", default=None)
    m.add_argument("--llm-base-url", default=None)
    m.add_argument("--config", "-c")

    t = sub.add_parser("check-llm", help="hacer una llamada mínima para verificar clave y modelo")
    t.add_argument("--provider", default=None)
    t.add_argument("--model", default=None)
    t.add_argument("--llm-base-url", default=None)
    t.add_argument("--config", "-c")

    d = sub.add_parser("delta", help="mostrar análisis delta")
    _common(d)
    d.add_argument("--print-subspec", action="store_true")

    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    a = ap.parse_args(argv)
    load_dotenv()
    if a.cmd in ("models", "check-llm"):
        from .llm import make_client
        s = Settings.load(a.config, provider=a.provider, llm_base_url=a.llm_base_url,
                          model=getattr(a, "model", None))
        kw = {"base_url": s.llm_base_url} if s.llm_base_url else {}
        client = make_client(s.provider, s.model, **kw)
        try:
            if a.cmd == "models":
                print("\n".join(client.list_models()))
            else:
                print(f"Consultando a {s.provider} ({s.model})… la primera respuesta puede tardar hasta 1 minuto.",
                      flush=True)
                r = client.complete("Responde solo con la palabra OK.", "¿Funcionas?")
                print(f"Proveedor: {s.provider} · modelo: {s.model}\nRespuesta: {r.text.strip()[:80]}\n"
                      f"Tokens: {r.prompt_tokens} + {r.completion_tokens} · latencia {r.latency_s:.1f}s\n✅ Conexión correcta")
        except Exception as e:
            print(f"❌ {e}", file=sys.stderr)
            return 2
        return 0

    if a.cmd == "delta":
        s = Settings.load(a.config, spec_path=a.spec_path, base_ref=a.base_ref, head_ref=a.head_ref)
        new = load_spec_at_ref(s.spec_path, s.head_ref) if s.head_ref else load_spec_file(s.spec_path)
        old = load_spec_file(a.old_spec) if a.old_spec else load_spec_at_ref(s.spec_path, s.base_ref)
        delta = compute_delta(old, new)
        print(json.dumps(delta.to_dict(), indent=2, ensure_ascii=False))
        if a.print_subspec:
            print(dump_spec(build_subspec(new, delta.targets)))
        return 0

    from .pipeline import run  # import diferido: evita costo en `delta`
    s = Settings.load(
        a.config, spec_path=a.spec_path, base_ref=a.base_ref, head_ref=a.head_ref, mode=a.mode,
        base_url=a.base_url, provider=a.provider, model=a.model, llm_base_url=a.llm_base_url,
        max_heal_iterations=a.max_heal_iterations, heal_policy=a.heal_policy,
        output_dir=a.output_dir, fail_on=a.fail_on,
    )
    from .llm import QuotaExhaustedError
    try:
        res = run(s, old_spec_path=a.old_spec, run_id=a.run_id)
    except QuotaExhaustedError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 4
    out = Path(s.output_dir) / (a.run_id or s.mode)
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        print((out / "report.md").read_text(encoding="utf-8"))
    if res.get("status") == "api_unreachable":
        print("ERROR: la API bajo prueba no responde", file=sys.stderr)
        return 3
    if s.fail_on == "never":
        return 0
    if s.fail_on == "any" and (res.get("assertion_failures") or res.get("runtime_errors")):
        return 1
    if s.fail_on == "regression" and res.get("assertion_failures"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
