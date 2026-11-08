import uuid
import pytest
from jsonschema import validate

USERS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["email", "id"],
                "properties": {
                    "email": {"type": "string"},
                    "is_active": {"type": "boolean"},
                    "is_superuser": {"type": "boolean"},
                    "full_name": {"type": ["string", "null"]},
                    "id": {"type": "string"},
                    "created_at": {"type": ["string", "null"]},
                },
            },
        },
        "count": {"type": "integer"},
    },
}

ITEM_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["title", "id", "owner_id"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "id": {"type": "string"},
        "owner_id": {"type": "string"},
        "created_at": {"type": ["string", "null"]},
    },
}

MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"},
    },
}

HTTP_VALIDATION_ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "detail": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["loc", "msg", "type"],
                "properties": {
                    "loc": {
                        "type": "array",
                        "items": {"type": ["string", "integer"]},
                    },
                    "msg": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        }
    },
}


# ============================================================================
# Tests: GET /api/v1/users/
# ============================================================================


def test_get_users_default_params_success(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(body["data"], list)
    assert isinstance(body["count"], int)
    assert body["count"] >= len(body["data"])


def test_get_users_with_valid_pagination(api):
    response = api.get("/api/v1/users/", params={"skip": 0, "limit": 5})
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=USERS_PUBLIC_SCHEMA)
    assert len(body["data"]) <= 5


def test_get_users_invalid_skip_type_error(api):
    response = api.get("/api/v1/users/", params={"skip": "not_an_int"})
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)
    assert "detail" in body


def test_get_users_invalid_limit_type_error(api):
    response = api.get("/api/v1/users/", params={"limit": "abc"})
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)
    assert "detail" in body


# ============================================================================
# Tests: PATCH /api/v1/users/me/password
# ============================================================================


def test_patch_users_me_password_validation_error_missing_fields(api):
    response = api.patch("/api/v1/users/me/password", json={})
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_short_password(api):
    payload = {
        "current_password": "short",
        "new_password": "short",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_long_password(api):
    payload = {
        "current_password": "a" * 129,
        "new_password": "b" * 129,
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ============================================================================
# Tests: POST /api/v1/items/
# ============================================================================


def test_post_items_success(api):
    payload = {
        "title": f"Item_{uuid.uuid4().hex[:8]}",
        "description": "Item for testing create operation",
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=ITEM_PUBLIC_SCHEMA)
    assert body["title"] == payload["title"]
    assert body["description"] == payload["description"]
    assert "id" in body
    assert "owner_id" in body

    # Cleanup item
    item_id = body["id"]
    api.delete(f"/api/v1/items/{item_id}")


def test_post_items_minimal_fields_success(api):
    payload = {"title": f"Minimal_{uuid.uuid4().hex[:8]}"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=ITEM_PUBLIC_SCHEMA)
    assert body["title"] == payload["title"]
    assert body["description"] is None

    # Cleanup item
    item_id = body["id"]
    api.delete(f"/api/v1/items/{item_id}")


def test_post_items_missing_required_title(api):
    payload = {"description": "No title provided"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_empty_title_validation_error(api):
    payload = {"title": ""}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_title_too_long_validation_error(api):
    payload = {"title": "a" * 256}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ============================================================================
# Tests: PUT /api/v1/items/{id}
# ============================================================================


def test_put_item_success(api):
    create_res = api.post(
        "/api/v1/items/",
        json={"title": f"Initial_{uuid.uuid4().hex[:8]}", "description": "Init desc"},
    )
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    try:
        update_payload = {
            "title": f"Updated_{uuid.uuid4().hex[:8]}",
            "description": "Updated description content",
        }
        response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
        assert response.status_code == 200
        body = response.json()
        validate(instance=body, schema=ITEM_PUBLIC_SCHEMA)
        assert body["id"] == item_id
        assert body["title"] == update_payload["title"]
        assert body["description"] == update_payload["description"]
    finally:
        api.delete(f"/api/v1/items/{item_id}")


def test_put_item_invalid_uuid(api):
    response = api.put("/api/v1/items/invalid-uuid-format", json={"title": "New Title"})
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_validation_error_empty_title(api):
    create_res = api.post(
        "/api/v1/items/", json={"title": f"Item_{uuid.uuid4().hex[:8]}"}
    )
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    try:
        response = api.put(f"/api/v1/items/{item_id}", json={"title": ""})
        assert response.status_code == 422
        body = response.json()
        validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)
    finally:
        api.delete(f"/api/v1/items/{item_id}")


# ============================================================================
# Tests: DELETE /api/v1/items/{id}
# ============================================================================


def test_delete_item_success(api):
    create_res = api.post(
        "/api/v1/items/", json={"title": f"ToDelete_{uuid.uuid4().hex[:8]}"}
    )
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    body = response.json()
    validate(instance=body, schema=MESSAGE_SCHEMA)
    assert "message" in body


def test_delete_item_invalid_uuid(api):
    response = api.delete("/api/v1/items/not-a-valid-uuid")
    assert response.status_code == 422
    body = response.json()
    validate(instance=body, schema=HTTP_VALIDATION_ERROR_SCHEMA)
