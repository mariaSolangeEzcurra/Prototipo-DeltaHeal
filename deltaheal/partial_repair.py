"""Reparación parcial ("patch mode") del archivo de pruebas.

En vez de reenviar el archivo completo y pedir de vuelta el archivo completo,
se envían solo:
  - la cabecera del módulo (imports, helpers y fixtures: lo que los tests usan),
  - las funciones/clases de test que fallaron,
y se pide al LLM SOLO las definiciones corregidas. Luego se reemplazan por nombre
en el archivo original. Los tests que ya funcionan no viajan ni se regeneran,
lo que reduce tokens de entrada y, sobre todo, de salida.

Si el archivo no compila o no se pudo colectar, se usa la reparación completa.
"""

from __future__ import annotations

import ast
import re

from .pytest_runner import RunResult


def _span(node: ast.stmt) -> tuple[int, int]:
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return start, node.end_lineno or node.lineno


def _is_def(node: ast.stmt) -> bool:
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))


def failing_toplevel_names(run: RunResult, include_assertions: bool = False) -> set[str]:
    """Nombres de nivel superior (función test_* o clase Test*) de los tests con defectos."""
    names: set[str] = set()
    cases = list(run.broken)
    if include_assertions:
        cases += [c for c in run.cases if c.outcome == "assertion"]
    for c in cases:
        classname, _, name = c.nodeid.rpartition("::")
        name = re.sub(r"\[.*$", "", name)
        # classname = "test_generated" o "test_generated.TestPets"
        parts = classname.split(".")
        if len(parts) > 1 and parts[-1].startswith("Test"):
            names.add(parts[-1])
        else:
            names.add(name)
    return names


def split_for_patch(code: str, names: set[str]) -> tuple[str, str] | None:
    """Devuelve (cabecera, código de las definiciones que fallaron) o None si no aplica."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    lines = code.splitlines()
    header_parts, failing_parts, found = [], [], set()
    for node in tree.body:
        a, b = _span(node)
        src = "\n".join(lines[a - 1:b])
        if _is_def(node) and node.name in names:
            failing_parts.append(src)
            found.add(node.name)
        elif _is_def(node) and (node.name.startswith("test") or node.name.startswith("Test")):
            continue  # tests que funcionan: no se envían
        else:
            header_parts.append(src)
    if not found:
        return None
    return "\n\n".join(header_parts), "\n\n\n".join(failing_parts)


def merge_patch(original: str, patch: str) -> str:
    """Reemplaza por nombre las definiciones del parche; agrega las nuevas y los imports faltantes."""
    orig_tree = ast.parse(original)
    patch_tree = ast.parse(patch)  # SyntaxError si el parche es inválido
    lines = original.splitlines()
    patch_lines = patch.splitlines()

    orig_defs = {n.name: n for n in orig_tree.body if _is_def(n)}
    replacements: list[tuple[int, int, str]] = []
    appended: list[str] = []
    new_imports: list[str] = []
    existing_imports = {ast.unparse(n) for n in orig_tree.body if isinstance(n, (ast.Import, ast.ImportFrom))}

    for node in patch_tree.body:
        a, b = _span(node)
        src = "\n".join(patch_lines[a - 1:b])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if ast.unparse(node) not in existing_imports:
                new_imports.append(src)
        elif _is_def(node):
            if node.name in orig_defs:
                oa, ob = _span(orig_defs[node.name])
                replacements.append((oa, ob, src))
            else:
                appended.append(src)
    if not replacements and not appended:
        raise ValueError("El parche no contiene definiciones")

    for oa, ob, src in sorted(replacements, reverse=True):
        lines[oa - 1:ob] = src.splitlines()
    out = "\n".join(lines).rstrip() + "\n"
    if appended:
        out += "\n\n" + "\n\n\n".join(appended) + "\n"
    if new_imports:
        out = "\n".join(new_imports) + "\n" + out
    ast.parse(out)  # verificación final
    return out
