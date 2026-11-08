import uuid
import pytest
import requests
from jsonschema import validate

# ---------------------------------------------------------------------------
# Schemas para validación según contrato OpenAPI
# ---------------------------------------------------------------------------

USER_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["email", "id"],
    "properties": {
        "email": {"type": "string", "maxLength": 255},
        "is_active": {"type": "boolean"},
        "is_superuser": {"type": "boolean"},
        "full_name": {"type": ["string", "null"], "maxLength": 255},
        "id": {"type": "string"},
        "created_at": {"type": ["string", "null"]},
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
        "title": {"type": "string", "minLength": 1, "maxLength": 255},
        "description": {"type": ["string", "null"], "maxLength": 255},
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
    "required": ["detail"],
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


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/users/
# ---------------------------------------------------------------------------


def test_get_users_default_pagination(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)
    assert data["count"] >= 0


def test_get_users_with_valid_query_params(api):
    response = api.get("/api/v1/users/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert len(data["data"]) <= 10


def test_get_users_invalid_query_params(api):
    response = api.get("/api/v1/users/", params={"skip": "invalid_number"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: PATCH /api/v1/users/me/password
# ---------------------------------------------------------------------------


def test_patch_user_me_password_validation_error_short_password(api):
    payload = {
        "current_password": "changethis",
        "new_password": "short",  # Requiere minLength 8
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_user_me_password_missing_fields(api):
    payload = {"new_password": "newpassword123"}
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/items/
# ---------------------------------------------------------------------------


def test_post_items_success(api):
    payload = {
        "title": f"Item Test {uuid.uuid4().hex[:8]}",
        "description": "Item description for testing",
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert "id" in data
    assert "owner_id" in data


def test_post_items_optional_description_null(api):
    payload = {
        "title": f"Item Without Description {uuid.uuid4().hex[:8]}",
        "description": None,
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] is None


def test_post_items_validation_error_missing_title(api):
    payload = {"description": "Item without required title"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_validation_error_empty_title(api):
    payload = {"title": ""}  # minLength: 1
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: PUT /api/v1/items/{id}
# ---------------------------------------------------------------------------


def test_put_items_success(api):
    # Crear ítem previo
    create_payload = {
        "title": f"Item To Update {uuid.uuid4().hex[:8]}",
        "description": "Original Description",
    }
    create_res = api.post("/api/v1/items/", json=create_payload)
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    # Actualizar ítem
    update_payload = {
        "title": f"Updated Title {uuid.uuid4().hex[:8]}",
        "description": "Updated Description",
    }
    response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id
    assert data["title"] == update_payload["title"]
    assert data["description"] == update_payload["description"]


def test_put_items_validation_error_invalid_uuid(api):
    update_payload = {"title": "Updated Title"}
    response = api.put("/api/v1/items/not-a-valid-uuid", json=update_payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_items_validation_error_empty_title(api):
    create_payload = {"title": f"Item To Test Validation {uuid.uuid4().hex[:8]}"}
    create_res = api.post("/api/v1/items/", json=create_payload)
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    update_payload = {"title": ""}  # minLength: 1
    response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: DELETE /api/v1/items/{id}
# ---------------------------------------------------------------------------


def test_delete_items_success(api):
    # Crear ítem para ser eliminado
    create_payload = {"title": f"Item To Delete {uuid.uuid4().hex[:8]}"}
    create_res = api.post("/api/v1/items/", json=create_payload)
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    # Eliminar ítem
    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_delete_items_validation_error_invalid_uuid(api):
    response = api.delete("/api/v1/items/not-a-valid-uuid")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)
