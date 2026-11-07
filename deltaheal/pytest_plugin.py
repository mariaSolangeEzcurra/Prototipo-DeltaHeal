"""Plugin de Pytest cargado con `-p deltaheal.pytest_plugin`.

- Provee la fixture `api` (requests.Session con base URL y headers de auth).
- Instrumenta `requests.Session.send` para registrar cada llamada HTTP real
  (método, URL, status, test) en un JSONL. Esto permite medir la cobertura de
  respuestas HTTP de forma idéntica para las tres configuraciones, incluida la
  herramienta tradicional (Schemathesis también usa requests).

Variables de entorno:
  API_BASE_URL          URL base de la API bajo prueba (obligatoria).
  DELTAHEAL_HTTP_LOG    ruta del JSONL de tráfico (opcional).
  DELTAHEAL_AUTH_HEADER "Nombre: valor" para autenticación (opcional).
  DELTAHEAL_HTTP_TIMEOUT timeout por request en segundos (default 15).
"""

from __future__ import annotations

import json
import os
import threading
from urllib.parse import urljoin

import pytest
import requests

_current_test = {"nodeid": None}
_lock = threading.Lock()
_original_send = requests.Session.send


def _log_path() -> str | None:
    return os.environ.get("DELTAHEAL_HTTP_LOG")


def _recording_send(self, request, **kwargs):
    kwargs.setdefault("timeout", float(os.environ.get("DELTAHEAL_HTTP_TIMEOUT", "15")))
    resp = _original_send(self, request, **kwargs)
    path = _log_path()
    if path:
        rec = {
            "method": (request.method or "").upper(),
            "url": request.url,
            "status": resp.status_code,
            "test": _current_test["nodeid"],
        }
        with _lock, open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    return resp


class BaseUrlSession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.rstrip("/") + "/"

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        if not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url, url.lstrip("/"))
        return super().request(method, url, *args, **kwargs)


def pytest_configure(config):
    requests.Session.send = _recording_send  # type: ignore[assignment]


def pytest_unconfigure(config):
    requests.Session.send = _original_send  # type: ignore[assignment]


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    _current_test["nodeid"] = item.nodeid


@pytest.fixture
def base_url() -> str:
    url = os.environ.get("API_BASE_URL")
    if not url:
        pytest.exit("API_BASE_URL no está definida", returncode=4)
    return url


@pytest.fixture
def api(base_url):
    s = BaseUrlSession(base_url)
    s.headers.update({"Accept": "application/json"})
    auth = os.environ.get("DELTAHEAL_AUTH_HEADER")
    if auth and ":" in auth:
        k, v = auth.split(":", 1)
        s.headers[k.strip()] = v.strip()
    yield s
    s.close()
