"""Línea de comandos de DeltaHeal: `python -m deltaheal <comando>` (o `deltaheal <comando>`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import MODES, Settings, UsageError, load_dotenv
from .delta import DeltaResult, build_subspec, compute_delta
from .progress import progress
from .spec_loader import GitError, dump_spec, load_spec_at_ref, load_spec_file

DEFAULTS = Settings()

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_ERROR = 2
EXIT_API_DOWN = 3
EXIT_QUOTA = 4
EXIT_CANCELLED = 5

DESCRIPTION = """\
DeltaHeal genera pruebas de regresión para APIs REST con IA, solo para los endpoints que
cambiaron en el contrato OpenAPI; las ejecuta contra la API y repara automáticamente las
pruebas con errores de código.
"""

EPILOG = """\
ejemplos:
  python -m deltaheal demo
  python -m deltaheal init
  python -m deltaheal delta --spec openapi.yaml --base-ref origin/main
  python -m deltaheal run --spec openapi.yaml --base-url http://localhost:8080
  python -m deltaheal run -c deltaheal.yaml --review

códigos de salida:
  0  sin posibles regresiones
  1  posibles regresiones (según --fail-on)
  2  error de uso, de configuración o de conexión con el proveedor de IA
  3  la API bajo prueba no responde
  4  cuota diaria del proveedor de IA agotada
  5  ejecución cancelada por el revisor (--review)

ayuda de cada comando:  python -m deltaheal <comando> --help
"""

MODES_HELP = """\
modos (--mode):
  deltaheal    análisis delta + auto-corrección (recomendado)
  traditional  Schemathesis, sin IA (referencia)
  llm_full     contrato completo, sin auto-corrección
  delta_only   análisis delta, sin auto-corrección
  full_heal    contrato completo, con auto-corrección
"""


# --------------------------------------------------------------------------- #
# Definición de comandos y opciones
# --------------------------------------------------------------------------- #

class _HelpFormatter(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):  # type: ignore[override]
        return super().add_usage(usage, actions, groups, "uso: " if prefix is None else prefix)


def _localize(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Ayuda en español: título de la sección de opciones y opción -h."""
    p._optionals.title = "opciones"
    p.add_argument("-h", "--help", action="help", help="mostrar esta ayuda y salir")
    return p


def _subparser(sub: Any, name: str, summary: str, description: str, epilog: str = "") -> argparse.ArgumentParser:
    return _localize(sub.add_parser(name, help=summary, description=description, epilog=epilog,
                                    formatter_class=_HelpFormatter, add_help=False))


def _add_spec_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("-c", "--config", metavar="ARCHIVO", help="archivo YAML de configuración (ver deltaheal init)")
    p.add_argument("--spec", dest="spec_path", metavar="RUTA",
                   help=f"contrato OpenAPI dentro del repositorio (por defecto: {DEFAULTS.spec_path})")
    p.add_argument("--base-ref", metavar="REF",
                   help=f"rama o commit base para comparar (por defecto: {DEFAULTS.base_ref})")
    p.add_argument("--head-ref", metavar="REF",
                   help="rama o commit con los cambios (por defecto: directorio de trabajo)")
    p.add_argument("--old-spec", metavar="RUTA", help="contrato base como archivo, en lugar de usar git")


def _add_llm_options(p: argparse.ArgumentParser, provider_default: str | None = None) -> None:
    default = provider_default or DEFAULTS.provider
    p.add_argument("--provider", default=provider_default, metavar="PROVEEDOR",
                   help=f"proveedor de IA: gemini, groq, ollama, openai, deepseek, anthropic o mock "
                        f"(por defecto: {default})")
    p.add_argument("--model", metavar="MODELO", help=f"modelo del proveedor (por defecto: {DEFAULTS.model} en gemini)")
    p.add_argument("--llm-base-url", metavar="URL", help="URL alternativa del proveedor de IA")


def build_parser() -> argparse.ArgumentParser:
    ap = _localize(argparse.ArgumentParser(prog="deltaheal", description=DESCRIPTION, epilog=EPILOG,
                                           formatter_class=_HelpFormatter, add_help=False))
    ap.add_argument("--version", action="version", version=f"deltaheal {__version__}",
                    help="mostrar la versión y salir")
    sub = ap.add_subparsers(dest="cmd", metavar="<comando>", title="comandos")

    r = _subparser(sub, "run", "ejecutar el flujo completo y generar el reporte",
                   "Detecta los endpoints que cambiaron, genera pruebas con IA, las ejecuta contra la API,\n"
                   "repara las pruebas con errores de código y genera el reporte (report.md y report.json).",
                   MODES_HELP)
    _add_spec_options(r)
    r.add_argument("--base-url", metavar="URL", help=f"URL de la API bajo prueba (por defecto: {DEFAULTS.base_url})")
    r.add_argument("--mode", choices=list(MODES), help=f"modo de ejecución (por defecto: {DEFAULTS.mode}); ver abajo")
    _add_llm_options(r)
    r.add_argument("--auth-header", metavar='"NOMBRE: VALOR"',
                   help='header de autenticación para la API, p. ej. "Authorization: Bearer <token>" '
                        "(alternativa: variable de entorno DELTAHEAL_AUTH_HEADER)")
    r.add_argument("--max-heal-iterations", type=int, metavar="N",
                   help=f"máximo de reparaciones automáticas (por defecto: {DEFAULTS.max_heal_iterations})")
    r.add_argument("--heal-policy", choices=["errors", "all"],
                   help="errors: repara solo errores de código (por defecto); all: también fallas de aserción")
    r.add_argument("--review", action="store_true",
                   help="revisión humana: pausa antes de ejecutar las pruebas para revisarlas, editarlas o cancelar")
    r.add_argument("--accepted", metavar="ARCHIVO",
                   help="YAML con fallas revisadas y aceptadas por el equipo (no bloquean el Pull Request)")
    r.add_argument("--fail-on", choices=["regression", "any", "never"],
                   help="cuándo terminar con código 1: regression (por defecto), any (también errores) o never")
    r.add_argument("--output-dir", metavar="CARPETA", help=f"carpeta de resultados (por defecto: {DEFAULTS.output_dir})")
    r.add_argument("--run-id", metavar="NOMBRE", help="subcarpeta de esta ejecución (por defecto: el modo)")
    r.add_argument("--json", action="store_true", help="imprimir el reporte completo en JSON")
    r.add_argument("--quiet", action="store_true", help="no mostrar el progreso de cada etapa")

    d = _subparser(sub, "delta", "mostrar qué endpoints cambiaron (sin API ni IA)",
                   "Compara la versión base y la nueva del contrato OpenAPI, endpoint por endpoint.\n"
                   "No ejecuta la API ni llama a la IA.")
    _add_spec_options(d)
    d.add_argument("--json", action="store_true", help="imprimir el resultado en JSON")
    d.add_argument("--print-subspec", action="store_true", help="imprimir el fragmento del contrato que se enviaría a la IA")

    m = _subparser(sub, "demo", "demostración guiada con la API de ejemplo",
                   "Inicia la API de ejemplo (demo_api/) y ejecuta dos escenarios:\n"
                   "  1. cambio en el contrato con la API funcionando correctamente;\n"
                   "  2. el mismo cambio con una regresión en la API (responde 500).\n"
                   "Con el proveedor simulado (mock, por defecto) no requiere internet ni clave de API.")
    _add_llm_options(m, provider_default="mock")
    m.add_argument("--scenario", choices=["both", "normal", "regression"], default="both",
                   help="escenarios a ejecutar (por defecto: both)")
    m.add_argument("--port", type=int, metavar="PUERTO", help="puerto de la API de ejemplo (por defecto: uno libre)")
    m.add_argument("--output-dir", default="deltaheal-out/demo", metavar="CARPETA",
                   help="carpeta de resultados (por defecto: deltaheal-out/demo)")
    m.add_argument("--pause", action="store_true", help="pausar entre escenarios (útil al presentar)")
    m.add_argument("--quiet", action="store_true", help="no mostrar el progreso de cada etapa")

    i = _subparser(sub, "init", "crear el archivo de configuración con un asistente",
                   "Crea deltaheal.yaml a partir de unas preguntas (contrato, URL de la API, rama base,\n"
                   "proveedor y modelo de IA). Detecta los contratos OpenAPI del repositorio.")
    i.add_argument("--file", default="deltaheal.yaml", metavar="RUTA", help="archivo a crear (por defecto: deltaheal.yaml)")
    i.add_argument("--yes", action="store_true", help="usar los valores detectados sin preguntar")
    i.add_argument("--force", action="store_true", help="sobrescribir el archivo si ya existe")

    t = _subparser(sub, "check-llm", "verificar la clave y el modelo del proveedor de IA",
                   "Hace una llamada mínima al proveedor de IA para verificar la clave y el modelo.")
    _add_llm_options(t)
    t.add_argument("-c", "--config", metavar="ARCHIVO", help="archivo YAML de configuración")

    ls = _subparser(sub, "models", "listar los modelos disponibles para la clave configurada",
                    "Lista los modelos que ofrece el proveedor de IA para la clave configurada.")
    ls.add_argument("--provider", metavar="PROVEEDOR", help=f"proveedor de IA (por defecto: {DEFAULTS.provider})")
    ls.add_argument("--llm-base-url", metavar="URL", help="URL alternativa del proveedor de IA")
    ls.add_argument("-c", "--config", metavar="ARCHIVO", help="archivo YAML de configuración")
    return ap


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #

def cmd_run(a: argparse.Namespace) -> int:
    from .human_review import console_reviewer
    from .pipeline import run  # import diferido: los otros comandos no lo necesitan

    s = Settings.load(
        a.config, spec_path=a.spec_path, base_ref=a.base_ref, head_ref=a.head_ref, mode=a.mode,
        base_url=a.base_url, provider=a.provider, model=a.model, llm_base_url=a.llm_base_url,
        auth_header=a.auth_header, max_heal_iterations=a.max_heal_iterations, heal_policy=a.heal_policy,
        accepted_file=a.accepted, output_dir=a.output_dir, fail_on=a.fail_on,
    )
    if a.review and not sys.stdin.isatty():
        raise ValueError("--review requiere una terminal interactiva")
    progress.enabled = not a.quiet
    res = run(s, old_spec_path=a.old_spec, run_id=a.run_id, reviewer=console_reviewer if a.review else None)
    progress.message("")
    if a.json:
        print(json.dumps(res, indent=2, ensure_ascii=False, default=str))
    else:
        print((Path(s.output_dir) / (a.run_id or s.mode) / "report.md").read_text(encoding="utf-8"))
    return exit_code(s, res)


def exit_code(s: Settings, res: dict[str, Any]) -> int:
    status = res.get("status")
    if status == "api_unreachable":
        print("ERROR: la API bajo prueba no responde", file=sys.stderr)
        return EXIT_API_DOWN
    if status == "review_cancelled":
        return EXIT_CANCELLED
    regressions = res.get("possible_regressions") or []
    if s.fail_on == "any" and (regressions or res.get("runtime_errors")):
        return EXIT_REGRESSION
    if s.fail_on == "regression" and regressions:
        return EXIT_REGRESSION
    return EXIT_OK


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def format_delta(delta: DeltaResult, new_spec: dict, base_label: str, head_label: str) -> str:
    rows = ([("nuevo", k) for k in delta.added] + [("modificado", k) for k in delta.modified]
            + [("eliminado", k) for k in delta.removed])
    lines = ["Análisis delta del contrato OpenAPI", f"  Base:   {base_label}", f"  Nuevo:  {head_label}", ""]
    if not rows:
        lines.append("  El contrato no cambió: no se generarían pruebas (0 tokens).")
        return "\n".join(lines)
    lines.append(f"  {'Estado':<11} {'Método':<7} Ruta")
    lines += [f"  {state:<11} {k.method.upper():<7} {k.path}" for state, k in rows]
    lines += ["", "  " + " · ".join([
        _plural(len(delta.added), "nuevo", "nuevos"), _plural(len(delta.modified), "modificado", "modificados"),
        _plural(len(delta.removed), "eliminado", "eliminados"), f"{len(delta.unchanged)} sin cambios"])]
    if delta.targets:
        full, sub = dump_spec(new_spec), dump_spec(build_subspec(new_spec, delta.targets))
        total = len(delta.targets) + len(delta.unchanged)
        lines.append(f"  Se generarían pruebas para {len(delta.targets)} de {total} operaciones; el contrato "
                     f"enviado a la IA sería {1 - len(sub) / max(1, len(full)):.0%} más corto.")
    else:
        lines.append("  No hay operaciones nuevas ni modificadas: no se generarían pruebas.")
    return "\n".join(lines)


def cmd_delta(a: argparse.Namespace) -> int:
    s = Settings.load(a.config, spec_path=a.spec_path, base_ref=a.base_ref, head_ref=a.head_ref)
    new = load_spec_at_ref(s.spec_path, s.head_ref) if s.head_ref else load_spec_file(s.spec_path)
    old = load_spec_file(a.old_spec) if a.old_spec else load_spec_at_ref(s.spec_path, s.base_ref)
    delta = compute_delta(old, new)
    if a.json:
        print(json.dumps(delta.to_dict(), indent=2, ensure_ascii=False))
    else:
        base_label = a.old_spec or f"{s.spec_path} en {s.base_ref} (git)"
        head_label = f"{s.spec_path}" + (f" en {s.head_ref} (git)" if s.head_ref else " (directorio de trabajo)")
        print(format_delta(delta, new, base_label, head_label))
    if a.print_subspec:
        print(dump_spec(build_subspec(new, delta.targets)))
    return EXIT_OK


def cmd_demo(a: argparse.Namespace) -> int:
    from .demo import run_demo
    progress.enabled = not a.quiet
    scenarios = None if a.scenario == "both" else [a.scenario]
    return run_demo(provider=a.provider, model=a.model, llm_base_url=a.llm_base_url, port=a.port,
                    output_dir=a.output_dir, scenarios=scenarios, pause=a.pause and sys.stdin.isatty())


def cmd_init(a: argparse.Namespace) -> int:
    from .init_config import next_steps, run_init
    target, provider = run_init(a.file, assume_yes=a.yes, force=a.force)
    print(f"✅ Configuración creada: {target}\n\nSiguientes pasos:\n{next_steps(target, provider)}")
    return EXIT_OK


def _llm_client(a: argparse.Namespace) -> tuple[Settings, Any]:
    from .llm import make_client
    s = Settings.load(a.config, provider=a.provider, llm_base_url=a.llm_base_url, model=getattr(a, "model", None))
    kw = {"base_url": s.llm_base_url} if s.llm_base_url else {}
    return s, make_client(s.provider, s.model, **kw)


def cmd_check_llm(a: argparse.Namespace) -> int:
    s, client = _llm_client(a)
    print(f"Consultando a {s.provider} ({s.model})… la primera respuesta puede tardar hasta 1 minuto.", flush=True)
    try:
        r = client.complete("Responde solo con la palabra OK.", "¿Funcionas?")
    except Exception as e:  # noqa: BLE001 - cualquier fallo del proveedor se informa igual
        print(f"❌ {e}", file=sys.stderr)
        return EXIT_ERROR
    print(f"Proveedor: {s.provider} · modelo: {s.model}\nRespuesta: {r.text.strip()[:80]}\n"
          f"Tokens: {r.prompt_tokens} + {r.completion_tokens} · latencia {r.latency_s:.1f} s\n✅ Conexión correcta")
    return EXIT_OK


def cmd_models(a: argparse.Namespace) -> int:
    _, client = _llm_client(a)
    try:
        print("\n".join(client.list_models()))
    except Exception as e:  # noqa: BLE001
        print(f"❌ {e}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


COMMANDS = {"run": cmd_run, "delta": cmd_delta, "demo": cmd_demo, "init": cmd_init,
            "check-llm": cmd_check_llm, "models": cmd_models}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    a = parser.parse_args(argv)
    if not a.cmd:
        parser.print_help()
        return EXIT_ERROR
    load_dotenv()

    from .llm import QuotaExhaustedError
    try:
        return COMMANDS[a.cmd](a)
    except QuotaExhaustedError as e:
        print(f"\n❌ {e}", file=sys.stderr)
        return EXIT_QUOTA
    except (UsageError, ValueError, FileNotFoundError, GitError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("\nInterrumpido.", file=sys.stderr)
        return 130
    finally:
        progress.enabled = False


if __name__ == "__main__":
    sys.exit(main())
