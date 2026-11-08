import uuid
import pytest
import requests
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
                    "input": {},
                    "ctx": {"type": "object"},
                },
            },
        }
    },
}


# --- Tests para GET /api/v1/users/ ---

def test_get_users_default_pagination_success(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)
    assert data["count"] >= len(data["data"])


def test_get_users_custom_pagination_success(api):
    response = api.get("/api/v1/users/", params={"skip": 0, "limit": 5})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert len(data["data"]) <= 5


def test_get_users_invalid_query_params_validation_error(api):
    response = api.get("/api/v1/users/", params={"skip": "invalid_integer"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests para PATCH /api/v1/users/me/password ---

def test_patch_users_me_password_validation_error_invalid_lengths(api):
    # Contraseñas con longitud menor a la mínima requerida (8 caracteres)
    payload = {
        "current_password": "short",
        "new_password": "short"
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_missing_fields(api):
    payload = {
        "current_password": "changethis"
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests para POST /api/v1/items/ ---

def test_post_items_success(api):
    unique_title = f"Item {uuid.uuid4()}"
    payload = {
        "title": unique_title,
        "description": "Item description for testing"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == unique_title
    assert data["description"] == "Item description for testing"
    assert "id" in data
    assert "owner_id" in data


def test_post_items_minimal_payload_success(api):
    unique_title = f"Minimal Item {uuid.uuid4()}"
    payload = {
        "title": unique_title
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == unique_title


def test_post_items_validation_error_missing_required(api):
    payload = {
        "description": "Item without title"
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_validation_error_empty_title(api):
    payload = {
        "title": ""
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests para PUT /api/v1/items/{id} ---

def test_put_item_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item To Update"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    updated_title = f"Updated Item {uuid.uuid4()}"
    update_payload = {
        "title": updated_title,
        "description": "Updated Description"
    }
    response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id
    assert data["title"] == updated_title
    assert data["description"] == "Updated Description"


def test_put_item_validation_error_invalid_uuid(api):
    response = api.put("/api/v1/items/not-a-valid-uuid", json={"title": "Updated"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_validation_error_empty_title(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item For Error Test"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    response = api.put(f"/api/v1/items/{item_id}", json={"title": ""})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests para DELETE /api/v1/items/{id} ---

def test_delete_item_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item To Delete"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_delete_item_validation_error_invalid_uuid(api):
    response = api.delete("/api/v1/items/not-a-valid-uuid")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)
