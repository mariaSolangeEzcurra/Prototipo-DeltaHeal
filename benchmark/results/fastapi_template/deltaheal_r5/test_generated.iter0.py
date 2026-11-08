import uuid
import pytest
from jsonschema import validate

USERS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "count": {"type": "integer"},
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


def test_get_users_default_success(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert data["count"] >= 0


def test_get_users_with_pagination(api):
    response = api.get("/api/v1/users/", params={"skip": 0, "limit": 5})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert len(data["data"]) <= 5


def test_get_users_invalid_params_validation_error(api):
    response = api.get("/api/v1/users/", params={"skip": "not-an-integer"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_short_password(api):
    # La especificación exige minLength: 8. Enviamos contraseña demasiado corta.
    payload = {
        "current_password": "short",
        "new_password": "short",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_missing_field(api):
    payload = {
        "current_password": "changethis"
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_success(api):
    title = f"Item {uuid.uuid4().hex[:8]}"
    description = "Test description"
    payload = {
        "title": title,
        "description": description,
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == title
    assert data["description"] == description

    # Limpieza
    api.delete(f"/api/v1/items/{data['id']}")


def test_post_items_validation_error_missing_title(api):
    payload = {
        "description": "Missing title"
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


def test_put_items_success(api):
    # Crear un ítem primero
    initial_title = f"Item {uuid.uuid4().hex[:8]}"
    create_resp = api.post("/api/v1/items/", json={"title": initial_title})
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    try:
        updated_title = f"Updated {uuid.uuid4().hex[:8]}"
        updated_desc = "Updated description"
        update_payload = {
            "title": updated_title,
            "description": updated_desc,
        }
        response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
        assert response.status_code == 200
        data = response.json()
        validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
        assert data["id"] == item_id
        assert data["title"] == updated_title
        assert data["description"] == updated_desc
    finally:
        api.delete(f"/api/v1/items/{item_id}")


def test_put_items_validation_error_invalid_uuid(api):
    response = api.put("/api/v1/items/invalid-uuid", json={"title": "Updated"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_items_success(api):
    # Crear ítem para ser eliminado
    create_resp = api.post(
        "/api/v1/items/", json={"title": f"To Delete {uuid.uuid4().hex[:8]}"}
    )
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    # Eliminar
    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_delete_items_validation_error_invalid_uuid(api):
    response = api.delete("/api/v1/items/not-a-valid-uuid")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)
