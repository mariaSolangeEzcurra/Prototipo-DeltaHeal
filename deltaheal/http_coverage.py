"""Cobertura de respuestas HTTP.

Definición operativa (para el experimento):

    cobertura = |{(op, código) documentados ∩ observados}| / |{(op, código) documentados}|

- `op` recorre el conjunto objetivo (por defecto, las operaciones del delta),
  de modo que las tres configuraciones se miden sobre el mismo denominador.
- Los códigos documentados son las claves explícitas de `responses` (sin `default`).
  Se admiten rangos tipo `2XX`.
- Los códigos observados salen del tráfico HTTP real registrado por el plugin.
- También se reportan códigos observados NO documentados (posibles desviaciones del contrato).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .delta import OperationKey, documented_statuses, iter_operations


def _template_regex(path: str) -> re.Pattern[str]:
    parts = re.split(r"(\{[^}]+\})", path)
    rx = "".join("[^/]+" if p.startswith("{") else re.escape(p) for p in parts)
    return re.compile(f"^{rx}/?$")


class PathMatcher:
    def __init__(self, spec: dict[str, Any], base_url: str):
        self.base_path = urlparse(base_url).path.rstrip("/")
        entries = []
        for key, _, _ in iter_operations(spec):
            n_params = key.path.count("{")
            entries.append((n_params, -len(key.path), key, _template_regex(key.path)))
        # preferimos plantillas más específicas (menos parámetros, ruta más larga)
        self.entries = sorted(entries, key=lambda e: (e[0], e[1]))

    def match(self, method: str, url: str) -> OperationKey | None:
        path = urlparse(url).path
        if self.base_path and path.startswith(self.base_path):
            path = path[len(self.base_path):] or "/"
        m = method.lower()
        for _, _, key, rx in self.entries:
            if key.method == m and rx.match(path):
                return key
        return None


def _status_matches(code: int, documented: str) -> bool:
    documented = documented.upper()
    if documented.endswith("XX"):
        return str(code)[0] == documented[0]
    return str(code) == documented


@dataclass
class CoverageReport:
    documented_pairs: int = 0
    covered_pairs: int = 0
    per_operation: dict[str, dict[str, Any]] = field(default_factory=dict)
    undocumented_observed: dict[str, list[int]] = field(default_factory=dict)
    unmatched_requests: int = 0
    total_requests: int = 0

    @property
    def ratio(self) -> float:
        return self.covered_pairs / self.documented_pairs if self.documented_pairs else 0.0

    @property
    def operations_hit(self) -> int:
        return sum(1 for v in self.per_operation.values() if v["observed"])

    def to_dict(self) -> dict[str, Any]:
        return {
            "http_coverage": round(self.ratio, 4),
            "documented_pairs": self.documented_pairs,
            "covered_pairs": self.covered_pairs,
            "operations_hit": self.operations_hit,
            "operations_total": len(self.per_operation),
            "total_requests": self.total_requests,
            "unmatched_requests": self.unmatched_requests,
            "undocumented_observed": self.undocumented_observed,
            "per_operation": self.per_operation,
        }


def read_http_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def compute_coverage(spec: dict[str, Any], targets: list[OperationKey], http_log: Path,
                     base_url: str) -> CoverageReport:
    matcher = PathMatcher(spec, base_url)
    observed: dict[OperationKey, set[int]] = {k: set() for k in targets}
    rep = CoverageReport()
    for rec in read_http_log(http_log):
        rep.total_requests += 1
        key = matcher.match(rec.get("method", ""), rec.get("url", ""))
        if key is None:
            rep.unmatched_requests += 1
            continue
        if key in observed:
            observed[key].add(int(rec["status"]))
    for key in targets:
        doc = documented_statuses(spec, key)
        obs = observed.get(key, set())
        covered = {d for d in doc if any(_status_matches(o, d) for o in obs)}
        undocumented = sorted(o for o in obs if not any(_status_matches(o, d) for d in doc))
        rep.documented_pairs += len(doc)
        rep.covered_pairs += len(covered)
        rep.per_operation[str(key)] = {
            "documented": sorted(doc),
            "observed": sorted(obs),
            "covered": sorted(covered),
        }
        if undocumented:
            rep.undocumented_observed[str(key)] = undocumented
    return rep
