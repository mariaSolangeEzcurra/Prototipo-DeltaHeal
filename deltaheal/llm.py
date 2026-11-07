"""Clientes LLM sin dependencias de SDK (solo `requests`).

Proveedores:
- gemini:    Google Gemini (nivel GRATUITO de Google AI Studio) vía su endpoint compatible con OpenAI.
- groq:      Groq (nivel gratuito).
- ollama:    modelos locales, gratis y sin límites (requiere Ollama instalado).
- deepseek / openai: APIs de pago compatibles con /chat/completions.
- anthropic: API de Mensajes de Anthropic.
- mock:      generador determinista offline para pruebas del pipeline (0 costo).

Todos devuelven los tokens reportados por el proveedor, que son la base de
la métrica de eficiencia del experimento.
"""

from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

import requests
import yaml


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    latency_s: float
    finish_reason: str = ""
    reasoning_tokens: int = 0     # tokens de "pensamiento" (se facturan como salida)

    @property
    def truncated(self) -> bool:
        return self.finish_reason in ("length", "max_tokens", "MAX_TOKENS")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class LLMClient(Protocol):
    model: str

    def complete(self, system: str, user: str) -> LLMResponse: ...


# --------------------------------------------------------------------------- #
# Proveedores gratuitos / compatibles con OpenAI (presets)
# --------------------------------------------------------------------------- #

# rpm: llamadas por minuto que se respetan por defecto (margen bajo el límite gratuito).
PRESETS: dict[str, dict[str, Any]] = {
    "gemini":   {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                 "key_env": "GEMINI_API_KEY", "send_seed": False, "rpm": 8,
                 "reasoning_effort": "low"},
    "groq":     {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY", "rpm": 20},
    "ollama":   {"base_url": "http://localhost:11434/v1", "key_env": None, "rpm": 0, "timeout": 900},
    "deepseek": {"base_url": "https://api.deepseek.com", "key_env": "DEEPSEEK_API_KEY", "rpm": 0},
    "openai":   {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY", "rpm": 0},
}


class QuotaExhaustedError(RuntimeError):
    """La cuota (normalmente diaria) del nivel gratuito se agotó: reintentar no sirve."""


_DAILY_HINTS = ("per day", "perday", "requests_per_day", "per_day", "daily", "PerDay",
                "insufficient_quota", "billing")


def _retry_after_seconds(r: requests.Response) -> float | None:
    h = r.headers.get("Retry-After")
    if h:
        try:
            return float(h)
        except ValueError:
            pass
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', r.text or "")
    if m:
        return float(m.group(1))
    m = re.search(r"try again in (\d+(?:\.\d+)?)s", r.text or "", re.I)
    return float(m.group(1)) if m else None


def _say(msg: str) -> None:
    import sys
    print(f"   ⏳ {msg}", file=sys.stderr, flush=True)


def _post_with_retries(url: str, headers: dict[str, str], payload: dict[str, Any],
                       timeout: int, retries: int = 6) -> dict[str, Any]:
    delay = 5.0
    for attempt in range(retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as e:
            if attempt < retries:
                _say(f"sin respuesta del proveedor LLM ({type(e).__name__}); reintento {attempt + 1}/{retries} "
                     f"en {delay:.0f} s")
                time.sleep(delay + random.random())
                delay = min(delay * 2, 120)
                continue
            raise
        if r.status_code == 429:
            body = r.text or ""
            wait = _retry_after_seconds(r)
            if any(h.lower() in body.lower() for h in _DAILY_HINTS) and (wait is None or wait > 600):
                raise QuotaExhaustedError(
                    "Se agotó la cuota diaria del nivel gratuito del proveedor LLM. "
                    "Vuelve a ejecutar mañana: el benchmark continúa donde quedó.\n" + body[:500])
            if attempt < retries:
                w = min(max(wait or delay, 1.0), 180)
                _say(f"límite por minuto del nivel gratuito (429); espero {w:.0f} s y reintento "
                     f"({attempt + 1}/{retries})")
                time.sleep(w + random.random())
                delay = min(delay * 2, 120)
                continue
            raise QuotaExhaustedError("Límite de peticiones persistente (429).\n" + body[:500])
        if r.status_code in (500, 502, 503, 504, 529) and attempt < retries:
            _say(f"el proveedor LLM respondió {r.status_code} (servidor ocupado); reintento "
                 f"{attempt + 1}/{retries} en {delay:.0f} s")
            time.sleep(delay + random.random())
            delay = min(delay * 2, 120)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Error HTTP {r.status_code} del proveedor LLM: {(r.text or '')[:800]}")
        return r.json()
    raise RuntimeError("Fallo tras reintentos")


class _Throttle:
    """Espaciado mínimo entre llamadas para no superar el límite por minuto del nivel gratuito."""
    _last: dict[str, float] = {}

    @classmethod
    def wait(cls, key: str, rpm: float) -> None:
        if not rpm:
            return
        gap = 60.0 / rpm
        now = time.monotonic()
        last = cls._last.get(key)
        if last is not None and now - last < gap:
            time.sleep(gap - (now - last))
        cls._last[key] = time.monotonic()


class OpenAICompatibleClient:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None,
                 temperature: float = 0.0, max_tokens: int = 8000, seed: int | None = None,
                 timeout: int | None = None, provider: str = "openai", rpm: float | None = None,
                 reasoning_effort: str | None = None):
        preset = PRESETS.get(provider, PRESETS["openai"])
        self.model = model
        self.provider = provider
        self.base_url = (base_url or (os.getenv("OPENAI_BASE_URL") if provider == "openai" else None)
                         or preset["base_url"]).rstrip("/")
        key_env = preset.get("key_env")
        self.api_key = api_key or (os.getenv(key_env, "") if key_env else "") or os.getenv("OPENAI_API_KEY", "")
        if provider == "ollama":
            self.api_key = api_key or "ollama"
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.seed = seed if preset.get("send_seed", True) else None
        self.timeout = timeout or preset.get("timeout", 300)
        self.rpm = preset.get("rpm", 0) if rpm is None else rpm
        # Limita el "pensamiento" de modelos de razonamiento para que no consuma todo el
        # presupuesto de salida y deje el código cortado. "" = no enviar el parámetro.
        self.reasoning_effort = (preset.get("reasoning_effort") if reasoning_effort is None
                                 else reasoning_effort) or None

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def complete(self, system: str, user: str) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort
        _Throttle.wait(self.base_url, self.rpm)
        t0 = time.perf_counter()
        url = f"{self.base_url}/chat/completions"
        try:
            data = _post_with_retries(url, self._headers(), payload, self.timeout)
        except RuntimeError as e:
            # Si el modelo no admite reasoning_effort, se reintenta sin él (y se recuerda).
            if "reasoning_effort" in payload and "HTTP 400" in str(e):
                payload.pop("reasoning_effort")
                self.reasoning_effort = None
                data = _post_with_retries(url, self._headers(), payload, self.timeout)
            else:
                raise
        dt = time.perf_counter() - t0
        usage = data.get("usage") or {}
        choice = (data.get("choices") or [{}])[0]
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        details = usage.get("completion_tokens_details") or {}
        reasoning = int(details.get("reasoning_tokens", 0) or 0)
        total = int(usage.get("total_tokens", 0) or 0)
        # Algunos proveedores (p. ej. Gemini) no incluyen el pensamiento en completion_tokens:
        # se factura como salida, así que se suma para que el costo y los tokens sean reales.
        if total > prompt + completion:
            reasoning = max(reasoning, total - prompt - completion)
            completion = total - prompt
        return LLMResponse(
            text=(choice.get("message") or {}).get("content") or "",
            prompt_tokens=prompt,
            completion_tokens=completion,
            model=data.get("model", self.model),
            latency_s=dt,
            finish_reason=str(choice.get("finish_reason") or ""),
            reasoning_tokens=reasoning,
        )

    def list_models(self) -> list[str]:
        r = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"Error HTTP {r.status_code}: {r.text[:500]}")
        return sorted(m.get("id", "") for m in r.json().get("data", []))


class AnthropicClient:
    def __init__(self, model: str, api_key: str | None = None, temperature: float = 0.0,
                 max_tokens: int = 8000, base_url: str | None = None, timeout: int = 300):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")
        self.timeout = timeout

    def complete(self, system: str, user: str) -> LLMResponse:
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        t0 = time.perf_counter()
        data = _post_with_retries(f"{self.base_url}/v1/messages", headers, payload, self.timeout)
        dt = time.perf_counter() - t0
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage") or {}
        return LLMResponse(
            text=text,
            prompt_tokens=int(usage.get("input_tokens", 0)),
            completion_tokens=int(usage.get("output_tokens", 0)),
            model=data.get("model", self.model),
            latency_s=dt,
        )


# --------------------------------------------------------------------------- #
# Mock determinista
# --------------------------------------------------------------------------- #

_SPEC_RE = re.compile(r"<openapi_spec>\s*(.*?)\s*</openapi_spec>", re.S)
_CODE_RE = re.compile(r"<(?:current_code|failing_tests)>\s*(.*?)\s*</(?:current_code|failing_tests)>", re.S)
_INJECTED = "undefined_helper_from_mock()"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _sample_from_schema(spec: dict[str, Any], schema: dict[str, Any] | None, depth: int = 0) -> Any:
    from .delta import resolve_pointer
    if not schema or depth > 4:
        return None
    if "$ref" in schema:
        try:
            schema = resolve_pointer(spec, schema["$ref"])
        except Exception:
            return None
    if "example" in schema:
        return schema["example"]
    if "enum" in schema:
        return schema["enum"][0]
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        props = schema.get("properties", {})
        req = schema.get("required", list(props))
        return {k: _sample_from_schema(spec, props[k], depth + 1) for k in req if k in props}
    if t == "array":
        item = _sample_from_schema(spec, schema.get("items"), depth + 1)
        return [] if item is None else [item]
    if t == "integer":
        return int(schema.get("minimum", 1))
    if t == "number":
        return float(schema.get("minimum", 1.0))
    if t == "boolean":
        return True
    if t == "string":
        return {"date-time": "2024-01-01T00:00:00Z", "date": "2024-01-01", "email": "a@b.com"}.get(
            schema.get("format", ""), "test")
    return None


class MockClient:
    """Genera pruebas simples a partir de la spec del prompt.

    Con `inject_error=True` introduce un NameError en la primera generación para
    ejercitar el bucle de self-healing; al recibir un prompt de reparación lo corrige.
    """

    def __init__(self, model: str = "mock-1", inject_error: bool = True, **_: Any):
        self.model = model
        self.inject_error = inject_error

    def complete(self, system: str, user: str) -> LLMResponse:
        t0 = time.perf_counter()
        code_m = _CODE_RE.search(user)
        if code_m:  # prompt de reparación
            code = code_m.group(1)
            code = re.sub(r"^```(?:python)?\s*|\s*```$", "", code.strip())
            out = code.replace(f"    {_INJECTED}\n", "")
        else:
            spec_m = _SPEC_RE.search(user)
            spec = yaml.safe_load(spec_m.group(1)) if spec_m else {}
            out = self._generate(spec or {})
        text = f"```python\n{out}\n```"
        return LLMResponse(text, _estimate_tokens(system + user), _estimate_tokens(text),
                           self.model, time.perf_counter() - t0)

    def _generate(self, spec: dict[str, Any]) -> str:
        from .delta import iter_operations
        lines = ["import pytest", ""]
        first = True
        for key, op, item in iter_operations(spec):
            params = list(item.get("parameters", [])) + list(op.get("parameters", []))
            path = key.path
            query: dict[str, Any] = {}
            for p in params:
                if "$ref" in p:
                    from .delta import resolve_pointer
                    p = resolve_pointer(spec, p["$ref"])
                val = _sample_from_schema(spec, p.get("schema") or {"type": p.get("type", "string")}) or 1
                if p.get("in") == "path":
                    path = path.replace("{" + p["name"] + "}", str(val))
                elif p.get("in") == "query" and p.get("required"):
                    query[p["name"]] = val
            body = None
            rb = op.get("requestBody", {})
            if "$ref" in rb:
                from .delta import resolve_pointer
                rb = resolve_pointer(spec, rb["$ref"])
            content = (rb.get("content") or {}).get("application/json")
            if content:
                body = _sample_from_schema(spec, content.get("schema"))
            codes = sorted(int(c) for c in (op.get("responses") or {}) if str(c).isdigit())
            name = re.sub(r"\W+", "_", f"{key.method}_{key.path}").strip("_")
            lines.append(f"def test_{name}(api):")
            if first and self.inject_error:
                lines.append(f"    {_INJECTED}")
                first = False
            args = [repr(path)]
            if query:
                args.append(f"params={query!r}")
            if body is not None:
                args.append(f"json={body!r}")
            lines.append(f"    r = api.{key.method}({', '.join(args)})")
            lines.append(f"    assert r.status_code in {codes or [200]}")
            lines.append("")
        if len(lines) == 2:
            lines += ["def test_placeholder():", "    assert True", ""]
        return "\n".join(lines)


def make_client(provider: str, model: str, **kw: Any) -> LLMClient:
    provider = provider.lower()
    if provider in ("openai-compatible", "vllm", "openrouter", "lmstudio"):
        provider = "openai"
    if provider in PRESETS:
        return OpenAICompatibleClient(model=model, provider=provider, **kw)
    if provider == "anthropic":
        kw.pop("seed", None)
        return AnthropicClient(model=model, **kw)
    if provider == "mock":
        return MockClient(model=model, **kw)
    raise ValueError(f"Proveedor LLM desconocido: {provider}")
