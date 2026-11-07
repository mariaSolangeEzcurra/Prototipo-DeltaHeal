"""Extracción y validación estática del código generado por el LLM."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_BLOCK_RE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S | re.I)


def extract_code(text: str) -> str:
    """Toma el bloque ```python``` más largo; si no hay bloque, usa el texto completo."""
    blocks = _BLOCK_RE.findall(text)
    if blocks:
        return max(blocks, key=len).strip() + "\n"
    # respuesta truncada: bloque abierto sin cerrar
    m = re.search(r"```(?:python|py)?[ \t]*\n(.*)$", text, re.S | re.I)
    if m:
        return m.group(1).strip() + "\n"
    return text.strip() + "\n"


@dataclass
class StaticCheck:
    ok: bool
    error: str | None
    test_count: int


def static_check(code: str) -> StaticCheck:
    """Valida sintaxis con `ast` y cuenta funciones test_* (también dentro de clases Test*)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return StaticCheck(False, f"SyntaxError: {e.msg} (línea {e.lineno}): {(e.text or '').strip()}",
                           count_tests_regex(code))
    return StaticCheck(True, None, count_tests_ast(tree))


def count_tests_ast(tree: ast.AST) -> int:
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            n += 1
    return n


def count_tests_regex(code: str) -> int:
    return len(re.findall(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", code, re.M))
