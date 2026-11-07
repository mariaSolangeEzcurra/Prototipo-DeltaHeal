"""Clientes LLM: se simula la respuesta HTTP del proveedor (sin red)."""

from deltaheal import llm


class _Resp:
    def __init__(self, data, status=200):
        self._d, self.status_code = data, status
        self.text, self.headers = "", {}

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


def test_openai_compatible_parses_usage(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, auth=headers.get("Authorization"), body=json)
        return _Resp({"model": "m", "choices": [{"message": {"content": "```python\nx=1\n```"}}],
                      "usage": {"prompt_tokens": 120, "completion_tokens": 30}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    c = llm.OpenAICompatibleClient("m", base_url="http://local/v1", api_key="k", seed=7)
    r = c.complete("sys", "user")
    assert seen["url"] == "http://local/v1/chat/completions" and seen["auth"] == "Bearer k"
    assert seen["body"]["seed"] == 7 and seen["body"]["messages"][0]["role"] == "system"
    assert (r.prompt_tokens, r.completion_tokens, r.total_tokens) == (120, 30, 150)


def test_anthropic_parses_usage(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json)
        return _Resp({"model": "c", "content": [{"type": "text", "text": "hola"}],
                      "usage": {"input_tokens": 50, "output_tokens": 5}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    r = llm.AnthropicClient("c", api_key="k").complete("sys", "user")
    assert seen["url"].endswith("/v1/messages") and seen["headers"]["x-api-key"] == "k"
    assert seen["body"]["system"] == "sys"
    assert (r.text, r.prompt_tokens, r.completion_tokens) == ("hola", 50, 5)


def test_retries_on_rate_limit(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp({}, status=429)
        return _Resp({"choices": [{"message": {"content": "ok"}}], "usage": {}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    assert llm.OpenAICompatibleClient("m", api_key="k").complete("s", "u").text == "ok"
    assert calls["n"] == 2


class _Resp429(_Resp):
    def __init__(self, text, headers=None):
        super().__init__({}, status=429)
        self.text, self.headers = text, headers or {}


def test_gemini_preset_uses_free_endpoint_and_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen.update(url=url, auth=headers.get("Authorization"), body=json)
        return _Resp({"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    c = llm.make_client("gemini", "gemini-2.5-flash", seed=3, rpm=0)
    c.complete("s", "u")
    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    assert seen["auth"] == "Bearer g-key"
    assert "seed" not in seen["body"]  # Gemini: no se envía seed


def test_rate_limit_waits_retry_delay(monkeypatch):
    calls, sleeps = {"n": 0}, []

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp429('{"error": {"details": [{"retryDelay": "12s"}]}}')
        return _Resp({"choices": [{"message": {"content": "ok"}}], "usage": {}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda s: sleeps.append(s))
    llm.OpenAICompatibleClient("m", api_key="k").complete("s", "u")
    assert calls["n"] == 2 and 12 <= sleeps[0] < 13.1


def test_daily_quota_raises_without_retrying(monkeypatch):
    import pytest
    calls = {"n": 0}

    def fake_post(url, headers, json, timeout):
        calls["n"] += 1
        return _Resp429('Quota exceeded for metric: GenerateRequestsPerDayPerProjectPerModel-FreeTier')

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    with pytest.raises(llm.QuotaExhaustedError):
        llm.OpenAICompatibleClient("m", api_key="k").complete("s", "u")
    assert calls["n"] == 1


def test_throttle_spaces_calls(monkeypatch):
    sleeps = []
    clock = {"t": 100.0}
    monkeypatch.setattr(llm.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(llm.time, "sleep", lambda s: sleeps.append(s))
    llm._Throttle._last.clear()
    llm._Throttle.wait("x", rpm=6)   # primera: no espera
    clock["t"] += 4
    llm._Throttle.wait("x", rpm=6)   # 60/6 = 10 s entre llamadas -> espera 6 s
    assert sleeps == [6.0]


def test_thinking_tokens_counted_and_truncation_flagged(monkeypatch):
    seen = {}

    def fake_post(url, headers, json, timeout):
        seen["body"] = json
        return _Resp({"choices": [{"message": {"content": "```python\nimport py"}, "finish_reason": "length"}],
                      "usage": {"prompt_tokens": 5920, "completion_tokens": 318, "total_tokens": 13920}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    r = llm.make_client("gemini", "gemini-2.5-flash", rpm=0).complete("s", "u")
    assert seen["body"]["reasoning_effort"] == "low"
    assert r.completion_tokens == 8000 and r.reasoning_tokens == 7682 and r.truncated


def test_reasoning_effort_dropped_if_rejected(monkeypatch):
    bodies = []

    def fake_post(url, headers, json, timeout):
        bodies.append(dict(json))
        if "reasoning_effort" in json:
            r = _Resp({}, status=400)
            r.text = "Unknown name reasoning_effort"
            return r
        return _Resp({"choices": [{"message": {"content": "ok"}}], "usage": {}})

    monkeypatch.setattr(llm.requests, "post", fake_post)
    c = llm.OpenAICompatibleClient("m", api_key="k", reasoning_effort="low")
    assert c.complete("s", "u").text == "ok"
    assert c.complete("s", "u").text == "ok"
    assert len(bodies) == 3  # 1 rechazo + 2 sin el parámetro (se recuerda)
