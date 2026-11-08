import uuid
import pytest
import requests
from jsonschema import validate

# JSON Schemas from OpenAPI Contract
USER_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["email", "id"],
    "properties": {
        "email": {"type": "string"},
        "is_active": {"type": "boolean"},
        "is_superuser": {"type": "boolean"},
        "full_name": {"type": ["string", "null"]},
        "id": {"type": "string"},
        "created_at": {"type": ["string", "null"]}
    }
}

USERS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {
            "type": "array",
            "items": USER_PUBLIC_SCHEMA
        },
        "count": {"type": "integer"}
    }
}

TOKEN_SCHEMA = {
    "type": "object",
    "required": ["access_token"],
    "properties": {
        "access_token": {"type": "string"},
        "token_type": {"type": "string"}
    }
}

MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"}
    }
}

ITEM_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["title", "id", "owner_id"],
    "properties": {
        "title": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "id": {"type": "string"},
        "owner_id": {"type": "string"},
        "created_at": {"type": ["string", "null"]}
    }
}

ITEMS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {
            "type": "array",
            "items": ITEM_PUBLIC_SCHEMA
        },
        "count": {"type": "integer"}
    }
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
                    "loc": {"type": "array"},
                    "msg": {"type": "string"},
                    "type": {"type": "string"}
                }
            }
        }
    }
}


def random_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------
# Login / Token Operations
# ---------------------------------------------------------

def test_post_login_access_token_success():
    res = requests.post(
        "http://localhost/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"}
    )
    # If base url differs in conftest, requests without relative url may not reach target,
    # so we test standard flow via api session's adapter if available or rely on standard auth.


def test_post_login_access_token_valid(base_url):
    res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"}
    )
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=TOKEN_SCHEMA)
    assert "access_token" in data


def test_post_login_access_token_missing_field_422(base_url):
    res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com"}
    )
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_login_test_token_authenticated_200(api):
    res = api.post("/api/v1/login/test-token")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_post_login_test_token_unauthenticated_401(base_url):
    res = requests.post(f"{base_url}/api/v1/login/test-token")
    assert res.status_code in [401, 403]


# ---------------------------------------------------------
# Password Recovery
# ---------------------------------------------------------

def test_post_password_recovery_success_200(api):
    email = "admin@example.com"
    res = api.post(f"/api/v1/password-recovery/{email}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_post_password_recovery_html_content_success_200(api):
    email = "admin@example.com"
    res = api.post(f"/api/v1/password-recovery-html-content/{email}")
    assert res.status_code == 200
    assert "html" in res.headers.get("content-type", "").lower()
    assert isinstance(res.text, str)


def test_post_reset_password_invalid_token_or_schema_422(api):
    # Missing required 'new_password'
    res = api.post("/api/v1/reset-password/", json={"token": "some-token"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_reset_password_short_password_422(api):
    # new_password minLength is 8
    res = api.post("/api/v1/reset-password/", json={"token": "some-token", "new_password": "short"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Users Operations (/api/v1/users/)
# ---------------------------------------------------------

def test_get_users_authenticated_200(api):
    res = api.get("/api/v1/users/?skip=0&limit=10")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert "data" in data
    assert isinstance(data["data"], list)
    assert "count" in data


def test_get_users_invalid_query_422(api):
    res = api.get("/api/v1/users/?limit=invalid_int")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_unauthenticated_401(base_url):
    res = requests.get(f"{base_url}/api/v1/users/")
    assert res.status_code in [401, 403]


def test_post_users_create_success_200(api):
    email = random_email()
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False
    }
    res = api.post("/api/v1/users/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_users_create_missing_password_422(api):
    res = api.post("/api/v1/users/", json={"email": random_email()})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_users_signup_success_200(base_url):
    email = random_email()
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Signup User"
    }
    res = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_users_signup_invalid_email_422(base_url):
    payload = {
        "email": "not-an-email",
        "password": "Password123!"
    }
    res = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# User Me Operations (/api/v1/users/me)
# ---------------------------------------------------------

def test_get_users_me_success_200(api):
    res = api.get("/api/v1/users/me")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_patch_users_me_success_200(api):
    payload = {"full_name": "Updated Admin Name"}
    res = api.patch("/api/v1/users/me", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "Updated Admin Name"


def test_patch_users_me_invalid_email_422(api):
    res = api.patch("/api/v1/users/me", json={"email": "not-a-valid-email"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_me_password_invalid_short_422(api):
    payload = {
        "current_password": "changethis",
        "new_password": "123"
    }
    res = api.patch("/api/v1/users/me/password", json=payload)
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_users_me_flow(base_url):
    # Create an ephemeral user to test delete me without deleting admin
    email = random_email()
    password = "UserPassword123!"
    reg = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": email, "password": password, "full_name": "Delete Me User"}
    )
    assert reg.status_code == 200

    login_res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": email, "password": password}
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    del_res = session.delete(f"{base_url}/api/v1/users/me")
    assert del_res.status_code == 200
    validate(instance=del_res.json(), schema=MESSAGE_SCHEMA)


# ---------------------------------------------------------
# Users by ID Operations (/api/v1/users/{user_id})
# ---------------------------------------------------------

def test_get_users_by_id_success_200(api):
    user_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password123!", "full_name": "Test Query"}
    )
    assert user_res.status_code == 200
    user_id = user_res.json()["id"]

    res = api.get(f"/api/v1/users/{user_id}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["id"] == user_id


def test_get_users_by_id_invalid_uuid_422(api):
    res = api.get("/api/v1/users/not-a-valid-uuid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_by_id_success_200(api):
    user_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password123!", "full_name": "Original"}
    )
    assert user_res.status_code == 200
    user_id = user_res.json()["id"]

    update_payload = {"full_name": "Patched Name", "is_active": True}
    res = api.patch(f"/api/v1/users/{user_id}", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "Patched Name"


def test_patch_users_by_id_invalid_uuid_422(api):
    res = api.patch("/api/v1/users/invalid-uuid", json={"full_name": "Test"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_users_by_id_success_200(api):
    user_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password123!", "full_name": "To Delete"}
    )
    assert user_res.status_code == 200
    user_id = user_res.json()["id"]

    res = api.delete(f"/api/v1/users/{user_id}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=MESSAGE_SCHEMA)


def test_delete_users_by_id_invalid_uuid_422(api):
    res = api.delete("/api/v1/users/invalid-uuid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Utils Operations
# ---------------------------------------------------------

def test_get_utils_health_check_200(api):
    res = api.get("/api/v1/utils/health-check/")
    assert res.status_code == 200
    assert isinstance(res.json(), bool)


def test_post_utils_test_email_success_201(api):
    res = api.post("/api/v1/utils/test-email/?email_to=admin@example.com")
    assert res.status_code == 201
    validate(instance=res.json(), schema=MESSAGE_SCHEMA)


def test_post_utils_test_email_invalid_email_422(api):
    res = api.post("/api/v1/utils/test-email/?email_to=not-an-email")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Items Operations (/api/v1/items/)
# ---------------------------------------------------------

def test_get_items_success_200(api):
    res = api.get("/api/v1/items/?skip=0&limit=5")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ITEMS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_items_invalid_param_422(api):
    res = api.get("/api/v1/items/?skip=invalid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_create_success_200(api):
    payload = {
        "title": f"Item_{uuid.uuid4().hex[:6]}",
        "description": "Item description"
    }
    res = api.post("/api/v1/items/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]


def test_post_items_create_missing_title_422(api):
    payload = {"description": "Missing title"}
    res = api.post("/api/v1/items/", json=payload)
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_item_by_id_success_200(api):
    create_res = api.post("/api/v1/items/", json={"title": "Test Get Item"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    res = api.get(f"/api/v1/items/{item_id}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id


def test_get_item_by_id_invalid_uuid_422(api):
    res = api.get("/api/v1/items/invalid-uuid-format")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_success_200(api):
    create_res = api.post("/api/v1/items/", json={"title": "To Update"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    update_payload = {"title": "Updated Title", "description": "Updated Description"}
    res = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == update_payload["title"]
    assert data["description"] == update_payload["description"]


def test_put_item_invalid_uuid_422(api):
    res = api.put("/api/v1/items/not-a-uuid", json={"title": "New Title"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_item_success_200(api):
    create_res = api.post("/api/v1/items/", json={"title": "To Delete"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    res = api.delete(f"/api/v1/items/{item_id}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=MESSAGE_SCHEMA)


def test_delete_item_invalid_uuid_422(api):
    res = api.delete("/api/v1/items/invalid-id")
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Private Operations (/api/v1/private/users/)
# ---------------------------------------------------------

def test_post_private_users_success_200(api):
    email = random_email()
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Private User",
        "is_verified": False
    }
    res = api.post("/api/v1/private/users/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_private_users_missing_fields_422(api):
    payload = {
        "email": random_email()
    }
    res = api.post("/api/v1/private/users/", json=payload)
    assert res.status_code == 422
    validate(instance=res.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)
