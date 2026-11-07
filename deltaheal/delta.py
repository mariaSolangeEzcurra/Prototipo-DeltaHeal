"""Análisis delta de contratos OpenAPI.

Idea: no basta con un diff textual línea a línea, porque un cambio en
`components/schemas/Pet` afecta a todas las operaciones que lo referencian
(directa o transitivamente). Por eso:

1. `git diff` detecta si el archivo de la spec cambió entre base y head
   (si no cambió, el pipeline termina sin gastar tokens).
2. Se cargan ambas versiones (`git show ref:path`) y se calcula, para cada
   operación (método + ruta), una huella canónica de la operación con todos
   sus `$ref` resueltos transitivamente.
3. Las operaciones nuevas o cuya huella cambió forman el delta.
4. Se construye una sub-especificación mínima: solo esas operaciones y los
   componentes que alcanzan por `$ref` (se conservan los `$ref` en vez de
   expandirlos, para no duplicar texto y ahorrar tokens).

Funciona con OpenAPI 3.x y Swagger 2.0 porque los `$ref` se tratan como
JSON Pointers genéricos.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterator

HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace")


# --------------------------------------------------------------------------- #
# JSON Pointer / $ref helpers
# --------------------------------------------------------------------------- #

def _unescape(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_pointer(spec: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"Solo se soportan $ref locales, se recibió: {ref}")
    node: Any = spec
    for raw in ref[2:].split("/"):
        token = _unescape(raw)
        if isinstance(node, list):
            node = node[int(token)]
        else:
            node = node[token]
    return node


def iter_refs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            yield ref
        for v in node.values():
            yield from iter_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from iter_refs(v)


def collect_refs_transitive(spec: dict[str, Any], node: Any) -> set[str]:
    seen: set[str] = set()
    stack = list(iter_refs(node))
    while stack:
        ref = stack.pop()
        if ref in seen or not ref.startswith("#/"):
            continue
        seen.add(ref)
        try:
            target = resolve_pointer(spec, ref)
        except (KeyError, IndexError, ValueError):
            continue
        stack.extend(iter_refs(target))
    return seen


def deref(spec: dict[str, Any], node: Any, _stack: tuple[str, ...] = ()) -> Any:
    """Expande $ref recursivamente (con protección de ciclos) para calcular huellas."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in _stack:
                return {"$cycle": ref}
            try:
                target = resolve_pointer(spec, ref)
            except (KeyError, IndexError, ValueError):
                return {"$unresolved": ref}
            return deref(spec, target, _stack + (ref,))
        return {k: deref(spec, v, _stack) for k, v in node.items()}
    if isinstance(node, list):
        return [deref(spec, v, _stack) for v in node]
    return node


# --------------------------------------------------------------------------- #
# Operaciones
# --------------------------------------------------------------------------- #

@dataclass(frozen=True, order=True)
class OperationKey:
    path: str
    method: str

    def __str__(self) -> str:
        return f"{self.method.upper()} {self.path}"


def iter_operations(spec: dict[str, Any]) -> Iterator[tuple[OperationKey, dict[str, Any], dict[str, Any]]]:
    """Itera (clave, operación, path_item)."""
    for path, item in (spec.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        if "$ref" in item:  # path item referenciado
            try:
                item = resolve_pointer(spec, item["$ref"])
            except Exception:
                continue
        for method in HTTP_METHODS:
            op = item.get(method)
            if isinstance(op, dict):
                yield OperationKey(path, method), op, item


def _effective_operation(spec: dict[str, Any], op: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    """Operación + parámetros a nivel de path + seguridad global (lo que realmente define el contrato)."""
    eff = dict(op)
    if item.get("parameters"):
        eff["__path_parameters"] = item["parameters"]
    if "security" not in op and spec.get("security"):
        eff["__global_security"] = spec["security"]
    # Swagger 2.0: consumes/produces/host/basePath globales afectan el contrato
    for k in ("consumes", "produces", "basePath"):
        if k in spec and k not in op:
            eff[f"__global_{k}"] = spec[k]
    return eff


def operation_fingerprint(spec: dict[str, Any], key: OperationKey) -> str | None:
    for k, op, item in iter_operations(spec):
        if k == key:
            resolved = deref(spec, _effective_operation(spec, op, item))
            canon = json.dumps(resolved, sort_keys=True, ensure_ascii=False, default=str)
            return hashlib.sha256(canon.encode()).hexdigest()
    return None


def fingerprints(spec: dict[str, Any]) -> dict[OperationKey, str]:
    out: dict[OperationKey, str] = {}
    for k, op, item in iter_operations(spec):
        resolved = deref(spec, _effective_operation(spec, op, item))
        canon = json.dumps(resolved, sort_keys=True, ensure_ascii=False, default=str)
        out[k] = hashlib.sha256(canon.encode()).hexdigest()
    return out


@dataclass
class DeltaResult:
    added: list[OperationKey] = field(default_factory=list)
    modified: list[OperationKey] = field(default_factory=list)
    removed: list[OperationKey] = field(default_factory=list)
    unchanged: list[OperationKey] = field(default_factory=list)

    @property
    def targets(self) -> list[OperationKey]:
        """Operaciones a testear: nuevas + modificadas."""
        return sorted(self.added + self.modified)

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.modified and not self.removed

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": [str(k) for k in self.added],
            "modified": [str(k) for k in self.modified],
            "removed": [str(k) for k in self.removed],
            "unchanged_count": len(self.unchanged),
        }


def compute_delta(old: dict[str, Any], new: dict[str, Any]) -> DeltaResult:
    fo, fn = fingerprints(old), fingerprints(new)
    res = DeltaResult()
    for k, h in sorted(fn.items()):
        if k not in fo:
            res.added.append(k)
        elif fo[k] != h:
            res.modified.append(k)
        else:
            res.unchanged.append(k)
    res.removed = sorted(k for k in fo if k not in fn)
    return res


# --------------------------------------------------------------------------- #
# Sub-especificación mínima
# --------------------------------------------------------------------------- #

def _set_pointer(dst: dict[str, Any], ref: str, value: Any) -> None:
    tokens = [_unescape(t) for t in ref[2:].split("/")]
    node = dst
    for t in tokens[:-1]:
        node = node.setdefault(t, {})
    node[tokens[-1]] = copy.deepcopy(value)


def build_subspec(spec: dict[str, Any], targets: list[OperationKey]) -> dict[str, Any]:
    """Spec válida que contiene solo `targets` y los componentes que alcanzan."""
    wanted = set(targets)
    sub: dict[str, Any] = {}
    for top in ("openapi", "swagger", "info", "servers", "host", "basePath", "schemes",
                "consumes", "produces", "security"):
        if top in spec:
            sub[top] = copy.deepcopy(spec[top])
    paths: dict[str, Any] = {}
    for k, op, item in iter_operations(spec):
        if k not in wanted:
            continue
        p = paths.setdefault(k.path, {})
        if item.get("parameters"):
            p["parameters"] = copy.deepcopy(item["parameters"])
        p[k.method] = copy.deepcopy(op)
    sub["paths"] = paths

    refs = collect_refs_transitive(spec, paths)
    # Esquemas de seguridad usados (no son $ref, se referencian por nombre)
    sec_names: set[str] = set()
    for item in paths.values():
        for m in HTTP_METHODS:
            for req in (item.get(m, {}) or {}).get("security", spec.get("security", [])) or []:
                sec_names.update(req.keys())
    for name in sec_names:
        if name in (spec.get("components", {}).get("securitySchemes") or {}):
            refs.add(f"#/components/securitySchemes/{name}")
        if name in (spec.get("securityDefinitions") or {}):
            refs.add(f"#/securityDefinitions/{name}")

    for ref in sorted(refs):
        try:
            _set_pointer(sub, ref, resolve_pointer(spec, ref))
        except (KeyError, IndexError, ValueError):
            continue
    return sub


def documented_statuses(spec: dict[str, Any], key: OperationKey) -> set[str]:
    """Códigos HTTP documentados explícitamente (se excluye `default`)."""
    for k, op, _ in iter_operations(spec):
        if k == key:
            codes = set()
            for code in (op.get("responses") or {}):
                c = str(code)
                if c.lower() == "default":
                    continue
                codes.add(c.upper())  # admite rangos tipo 2XX
            return codes
    return set()
