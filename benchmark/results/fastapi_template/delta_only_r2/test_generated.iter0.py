import uuid
import pytest
import requests
from jsonschema import validate

# ---------------------------------------------------------------------------
# Schemas JSON Schema según la especificación OpenAPI
# ---------------------------------------------------------------------------

VALIDATION_ERROR_SCHEMA = {
    "type": "object",
    "required": ["loc", "msg", "type"],
    "properties": {
        "loc": {
            "type": "array",
            "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
        },
        "msg": {"type": "string"},
        "type": {"type": "string"},
        "input": {},
        "ctx": {"type": "object"},
    },
}

HTTP_VALIDATION_ERROR_SCHEMA = {
    "type": "object",
    "required": ["detail"],
    "properties": {
        "detail": {
            "type": "array",
            "items": VALIDATION_ERROR_SCHEMA,
        }
    },
}

MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"},
    },
}

USER_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["email", "id"],
    "properties": {
        "email": {"type": "string", "maxLength": 255},
        "is_active": {"type": "boolean"},
        "is_superuser": {"type": "boolean"},
        "full_name": {"anyOf": [{"type": "string", "maxLength": 255}, {"type": "null"}]},
        "id": {"type": "string"},
        "created_at": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
}

USERS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {
            "type": "array",
            "items": USER_PUBLIC_SCHEMA,
        },
        "count": {"type": "integer"},
    },
}

ITEM_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["title", "id", "owner_id"],
    "properties": {
        "title": {"type": "string", "maxLength": 255, "minLength": 1},
        "description": {"anyOf": [{"type": "string", "maxLength": 255}, {"type": "null"}]},
        "id": {"type": "string"},
        "owner_id": {"type": "string"},
        "created_at": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    },
}

# ---------------------------------------------------------------------------
# Pruebas: GET /api/v1/users/
# ---------------------------------------------------------------------------

def test_get_users_default_params(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)
    assert data["count"] >= 0


def test_get_users_with_valid_pagination(api):
    response = api.get("/api/v1/users/?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert len(data["data"]) <= 5


def test_get_users_invalid_skip_type(api):
    response = api.get("/api/v1/users/?skip=invalid_number")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_invalid_limit_type(api):
    response = api.get("/api/v1/users/?limit=invalid_number")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Pruebas: PATCH /api/v1/users/me/password
# ---------------------------------------------------------------------------

def test_patch_users_me_password_invalid_current_password_short(api):
    payload = {
        "current_password": "short",
        "new_password": "newpassword123",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_invalid_new_password_short(api):
    payload = {
        "current_password": "changethis",
        "new_password": "short",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_missing_fields(api):
    payload = {
        "new_password": "newpassword123",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_exceeds_max_length(api):
    payload = {
        "current_password": "a" * 129,
        "new_password": "b" * 129,
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Pruebas: POST /api/v1/items/
# ---------------------------------------------------------------------------

def test_post_items_success_minimal(api):
    payload = {
        "title": f"Item {uuid.uuid4().hex[:8]}"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] is None or isinstance(data["description"], str)


def test_post_items_success_full(api):
    payload = {
        "title": f"Item {uuid.uuid4().hex[:8]}",
        "description": "A description for the test item",
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]


def test_post_items_missing_title(api):
    payload = {
        "description": "No title item"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_empty_title(api):
    payload = {
        "title": "",
        "description": "Empty title"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_title_too_long(api):
    payload = {
        "title": "x" * 256,
        "description": "Too long title"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Pruebas: PUT /api/v1/items/{id}
# ---------------------------------------------------------------------------

def test_put_item_success(api):
    create_payload = {
        "title": f"Initial {uuid.uuid4().hex[:8]}",
        "description": "Initial desc",
    }
    create_resp = api.post("/api/v1/items/", json=create_payload)
    assert create_resp.status_code == 200
    created_item = create_resp.json()
    item_id = created_item["id"]

    update_payload = {
        "title": f"Updated {uuid.uuid4().hex[:8]}",
        "description": "Updated desc",
    }
    update_resp = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert update_resp.status_code == 200
    data = update_resp.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id
    assert data["title"] == update_payload["title"]
    assert data["description"] == update_payload["description"]


def test_put_item_partial_update(api):
    create_payload = {
        "title": f"Initial {uuid.uuid4().hex[:8]}",
        "description": "Initial desc",
    }
    create_resp = api.post("/api/v1/items/", json=create_payload)
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    update_payload = {
        "title": f"NewTitle {uuid.uuid4().hex[:8]}",
    }
    update_resp = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert update_resp.status_code == 200
    data = update_resp.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == update_payload["title"]


def test_put_item_invalid_uuid(api):
    payload = {"title": "Updated Title"}
    response = api.put("/api/v1/items/not-a-valid-uuid", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_invalid_payload_empty_title(api):
    create_payload = {"title": f"Test {uuid.uuid4().hex[:8]}"}
    create_resp = api.post("/api/v1/items/", json=create_payload)
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    bad_payload = {"title": ""}
    response = api.put(f"/api/v1/items/{item_id}", json=bad_payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Pruebas: DELETE /api/v1/items/{id}
# ---------------------------------------------------------------------------

def test_delete_item_success(api):
    create_payload = {
        "title": f"To Delete {uuid.uuid4().hex[:8]}",
        "description": "Will be deleted",
    }
    create_resp = api.post("/api/v1/items/", json=create_payload)
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    delete_resp = api.delete(f"/api/v1/items/{item_id}")
    assert delete_resp.status_code == 200
    data = delete_resp.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)
    assert isinstance(data["message"], str)


def test_delete_item_invalid_uuid(api):
    response = api.delete("/api/v1/items/invalid-uuid-format")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)
