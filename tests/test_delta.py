import copy
import subprocess
from pathlib import Path

import yaml

from deltaheal.delta import (OperationKey, build_subspec, collect_refs_transitive, compute_delta,
                             documented_statuses)
from deltaheal.spec_io import git_spec_changed, load_spec_at_ref

ROOT = Path(__file__).resolve().parent.parent
V1 = yaml.safe_load((ROOT / "examples/demo_api/openapi_v1.yaml").read_text(encoding="utf-8"))
V2 = yaml.safe_load((ROOT / "examples/demo_api/openapi_v2.yaml").read_text(encoding="utf-8"))


def test_no_changes_is_empty():
    d = compute_delta(V1, copy.deepcopy(V1))
    assert d.is_empty and d.targets == []


def test_transitive_schema_change_marks_dependent_operations():
    d = compute_delta(V1, V2)
    assert OperationKey("/pets/{petId}", "patch") in d.added
    # PetIn cambió (age) → Pet (allOf PetIn) cambió → GET/POST que lo usan cambian
    assert {OperationKey("/pets", "get"), OperationKey("/pets", "post"),
            OperationKey("/pets/{petId}", "get")} <= set(d.modified)
    # DELETE no referencia esquemas que cambiaron
    assert OperationKey("/pets/{petId}", "delete") in d.unchanged


def test_removed_operation_detected():
    d = compute_delta(V2, V1)
    assert OperationKey("/pets/{petId}", "patch") in d.removed


def test_subspec_is_minimal_and_self_contained():
    targets = [OperationKey("/pets/{petId}", "patch")]
    sub = build_subspec(V2, targets)
    assert list(sub["paths"]) == ["/pets/{petId}"]
    assert set(sub["paths"]["/pets/{petId}"]) == {"parameters", "patch"}
    # todos los $ref del sub-spec resuelven dentro del sub-spec
    refs = collect_refs_transitive(sub, sub["paths"])
    assert refs == {"#/components/schemas/PetPatch", "#/components/schemas/Pet",
                    "#/components/schemas/PetIn"}


def test_path_level_parameter_change_is_detected():
    v3 = copy.deepcopy(V2)
    v3["paths"]["/pets/{petId}"]["parameters"][0]["schema"]["minimum"] = 1
    d = compute_delta(V2, v3)
    assert set(d.modified) == {OperationKey("/pets/{petId}", m) for m in ("get", "patch", "delete")}


def test_documented_statuses_excludes_default():
    v = copy.deepcopy(V2)
    v["paths"]["/pets"]["get"]["responses"]["default"] = {"description": "x"}
    assert documented_statuses(v, OperationKey("/pets", "get")) == {"200", "422"}


def test_cyclic_refs_do_not_loop():
    spec = {"openapi": "3.0.0", "paths": {"/n": {"get": {"responses": {"200": {
        "description": "", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Node"}}}}}}}},
        "components": {"schemas": {"Node": {"type": "object", "properties": {
            "child": {"$ref": "#/components/schemas/Node"}}}}}}
    spec2 = copy.deepcopy(spec)
    spec2["components"]["schemas"]["Node"]["properties"]["name"] = {"type": "string"}
    assert compute_delta(spec, spec2).modified == [OperationKey("/n", "get")]


def test_swagger2_definitions():
    s = {"swagger": "2.0", "paths": {"/a": {"get": {"responses": {"200": {
        "description": "", "schema": {"$ref": "#/definitions/A"}}}}}}, "definitions": {"A": {"type": "object"}}}
    s2 = copy.deepcopy(s)
    s2["definitions"]["A"]["properties"] = {"x": {"type": "string"}}
    d = compute_delta(s, s2)
    assert d.modified == [OperationKey("/a", "get")]
    assert "A" in build_subspec(s2, d.targets)["definitions"]


def test_git_based_flow(tmp_path):
    def git(*a):
        subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    spec = tmp_path / "openapi.yaml"
    spec.write_text(yaml.safe_dump(V1), encoding="utf-8")
    git("add", ".")
    git("commit", "-qm", "v1")
    assert not git_spec_changed("openapi.yaml", "HEAD", None, tmp_path)
    spec.write_text(yaml.safe_dump(V2), encoding="utf-8")
    assert git_spec_changed("openapi.yaml", "HEAD", None, tmp_path)
    old = load_spec_at_ref("openapi.yaml", "HEAD", tmp_path)
    assert compute_delta(old, V2).targets
