import pytest

from deltaheal.partial_repair import failing_toplevel_names, merge_patch, split_for_patch
from deltaheal.pytest_runner import CaseResult, RunResult

CODE = '''import pytest


def helper():
    return 1


@pytest.fixture
def pet(api):
    return {"id": 1}


def test_ok(api):
    assert helper() == 1


@pytest.mark.parametrize("x", [1, 2])
def test_broken(api, x):
    undefined_name()


class TestGroup:
    def test_inner(self, api):
        boom()
'''


def _run(*nodeids):
    return RunResult(1, 0.1, [CaseResult(n, "runtime_error", "NameError") for n in nodeids]
                     + [CaseResult("test_generated::test_ok", "passed")])


def test_failing_names_handles_params_and_classes():
    run = _run("test_generated::test_broken[1]", "test_generated.TestGroup::test_inner")
    assert failing_toplevel_names(run) == {"test_broken", "TestGroup"}


def test_split_sends_header_and_only_failing_tests():
    header, failing = split_for_patch(CODE, {"test_broken"})
    assert "def helper" in header and "def pet" in header and "test_ok" not in header
    assert "@pytest.mark.parametrize" in failing and "test_ok" not in failing and "TestGroup" not in failing


def test_merge_replaces_by_name_and_adds_imports():
    patch = '''import json

@pytest.mark.parametrize("x", [1, 2])
def test_broken(api, x):
    assert json.dumps(x)


def new_helper():
    return 2
'''
    out = merge_patch(CODE, patch)
    assert "undefined_name" not in out and "json.dumps(x)" in out
    assert out.startswith("import json") and "def new_helper" in out
    assert out.count("def test_broken") == 1 and "def test_ok" in out and "boom()" in out


def test_merge_rejects_invalid_patch():
    with pytest.raises(SyntaxError):
        merge_patch(CODE, "def test_broken(:\n    pass")
