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
                    "email": {"type": "string", "format": "email"},
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
                    "loc": {"type": "array", "items": {"type": ["string", "integer"]}},
                    "msg": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        }
    },
}


# --- Tests for GET /api/v1/users/ ---


def test_get_users_default_pagination_success(api):
    response = api.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)
    assert data["count"] >= len(data["data"])


def test_get_users_with_skip_and_limit_success(api):
    response = api.get("/api/v1/users/?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert len(data["data"]) <= 5


def test_get_users_invalid_skip_validation_error(api):
    response = api.get("/api/v1/users/?skip=invalid_number")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_invalid_limit_validation_error(api):
    response = api.get("/api/v1/users/?limit=not_an_int")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests for PATCH /api/v1/users/me/password ---


def test_patch_users_me_password_validation_error_short_password(api):
    payload = {
        "current_password": "short",
        "new_password": "short",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_missing_fields(api):
    payload = {
        "current_password": "changethis",
    }
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_validation_error_empty_body(api):
    response = api.patch("/api/v1/users/me/password", json={})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests for POST /api/v1/items/ ---


def test_post_items_success_minimal(api):
    item_title = f"Item {uuid.uuid4()}"
    payload = {"title": item_title}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == item_title
    assert data["description"] is None

    # Cleanup
    api.delete(f"/api/v1/items/{data['id']}")


def test_post_items_success_full(api):
    item_title = f"Item {uuid.uuid4()}"
    item_desc = "Test item description"
    payload = {"title": item_title, "description": item_desc}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == item_title
    assert data["description"] == item_desc

    # Cleanup
    api.delete(f"/api/v1/items/{data['id']}")


def test_post_items_validation_error_empty_title(api):
    payload = {"title": ""}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_validation_error_missing_title(api):
    payload = {"description": "Missing title item"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_validation_error_title_exceeds_max_length(api):
    payload = {"title": "a" * 256}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


# --- Tests for PUT /api/v1/items/{id} ---


def test_put_item_success(api):
    create_res = api.post("/api/v1/items/", json={"title": f"Initial {uuid.uuid4()}"})
    assert create_res.status_code == 200
    created_item = create_res.json()
    item_id = created_item["id"]

    try:
        updated_title = f"Updated {uuid.uuid4()}"
        updated_desc = "Updated description"
        put_res = api.put(
            f"/api/v1/items/{item_id}",
            json={"title": updated_title, "description": updated_desc},
        )
        assert put_res.status_code == 200
        put_data = put_res.json()
        validate(instance=put_data, schema=ITEM_PUBLIC_SCHEMA)
        assert put_data["id"] == item_id
        assert put_data["title"] == updated_title
        assert put_data["description"] == updated_desc
    finally:
        api.delete(f"/api/v1/items/{item_id}")


def test_put_item_validation_error_invalid_uuid(api):
    response = api.put("/api/v1/items/not-a-valid-uuid", json={"title": "New Title"})
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_validation_error_invalid_body(api):
    create_res = api.post("/api/v1/items/", json={"title": f"Test {uuid.uuid4()}"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    try:
        response = api.put(f"/api/v1/items/{item_id}", json={"title": ""})
        assert response.status_code == 422
        data = response.json()
        validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)
    finally:
        api.delete(f"/api/v1/items/{item_id}")


# --- Tests for DELETE /api/v1/items/{id} ---


def test_delete_item_success(api):
    create_res = api.post(
        "/api/v1/items/", json={"title": f"To Delete {uuid.uuid4()}"}
    )
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    delete_res = api.delete(f"/api/v1/items/{item_id}")
    assert delete_res.status_code == 200
    data = delete_res.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_delete_item_validation_error_invalid_uuid(api):
    response = api.delete("/api/v1/items/invalid-uuid-format")
    assert response.status_code == 422
    data = response.json()
    validate(instance=data, schema=HTTP_VALIDATION_ERROR_SCHEMA)
