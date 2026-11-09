from pathlib import Path

import yaml

from deltaheal.generated_code import extract_code, static_check
from deltaheal.http_coverage import PathMatcher, compute_coverage
from deltaheal.delta import OperationKey
from deltaheal.pytest_runner import _classify

ROOT = Path(__file__).resolve().parent.parent
V2 = yaml.safe_load((ROOT / "demo_api/openapi_v2.yaml").read_text(encoding="utf-8"))


def test_classify_outcomes():
    assert _classify("failure", "assert 404 in [200]", "") == "assertion"
    assert _classify("failure", "AssertionError: bad", "") == "assertion"
    assert _classify("failure", "NameError: name 'x' is not defined", "") == "runtime_error"
    assert _classify("failure", "KeyError: 'id'", "") == "runtime_error"
    assert _classify("failure", "jsonschema.exceptions.ValidationError: 1 is not 'string'", "") == "assertion"
    assert _classify("failure", "", "requests.exceptions.ConnectionError: Max retries exceeded") == "connection_error"
    assert _classify("error", "fixture 'client' not found", "") == "setup_error"


def test_extract_code_variants():
    assert extract_code("bla\n```python\nx = 1\n```\nfin") == "x = 1\n"
    assert extract_code("```python\nx = 1\n") == "x = 1\n"  # respuesta truncada
    assert extract_code("x = 2") == "x = 2\n"


def test_static_check_counts_tests():
    ok = static_check("def test_a():\n    pass\nclass TestX:\n    def test_b(self):\n        pass\n")
    assert ok.ok and ok.test_count == 2
    bad = static_check("def test_a(:\n    pass\n")
    assert not bad.ok and bad.test_count == 1 and "SyntaxError" in bad.error


def test_path_matcher_prefers_literal_and_strips_base_path():
    spec = {"paths": {"/pets/{id}": {"get": {}}, "/pets/mine": {"get": {}}}}
    m = PathMatcher(spec, "http://h:1/api/v3")
    assert m.match("GET", "http://h:1/api/v3/pets/mine") == OperationKey("/pets/mine", "get")
    assert m.match("GET", "http://h:1/api/v3/pets/7?x=1") == OperationKey("/pets/{id}", "get")
    assert m.match("POST", "http://h:1/api/v3/pets/7") is None


def test_coverage_ratio(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text(encoding="utf-8", data="\n".join([
        '{"method":"GET","url":"http://x/pets","status":200}',
        '{"method":"GET","url":"http://x/pets?limit=0","status":422}',
        '{"method":"GET","url":"http://x/pets/1","status":500}',
    ]))
    targets = [OperationKey("/pets", "get"), OperationKey("/pets/{petId}", "get")]
    rep = compute_coverage(V2, targets, log, "http://x")
    assert rep.documented_pairs == 4 and rep.covered_pairs == 2
    assert rep.ratio == 0.5
    assert rep.undocumented_observed == {"GET /pets/{petId}": [500]}
