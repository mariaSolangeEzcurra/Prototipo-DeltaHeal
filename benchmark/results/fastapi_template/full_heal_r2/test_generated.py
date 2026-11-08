import uuid
import pytest
import requests
from jsonschema import validate

# Schemas para validación según OpenAPI
SCHEMA_TOKEN = {
    "type": "object",
    "required": ["access_token"],
    "properties": {
        "access_token": {"type": "string"},
        "token_type": {"type": "string"},
    },
}

SCHEMA_USER_PUBLIC = {
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
}

SCHEMA_USERS_PUBLIC = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {"type": "array", "items": SCHEMA_USER_PUBLIC},
        "count": {"type": "integer"},
    },
}

SCHEMA_ITEM_PUBLIC = {
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

SCHEMA_ITEMS_PUBLIC = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {"type": "array", "items": SCHEMA_ITEM_PUBLIC},
        "count": {"type": "integer"},
    },
}

SCHEMA_MESSAGE = {
    "type": "object",
    "required": ["message"],
    "properties": {
        "message": {"type": "string"},
    },
}

SCHEMA_VALIDATION_ERROR = {
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
                    "type": {"type": "string"},
                },
            },
        }
    },
}


# --- Login & Authentication Endpoints ---

def test_post_login_access_token_success(base_url):
    res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"},
    )
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_TOKEN)
    assert data["token_type"] == "bearer"


def test_post_login_access_token_validation_error(base_url):
    res = requests.post(f"{base_url}/api/v1/login/access-token", data={})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_post_login_test_token_success(api):
    res = api.post("/api/v1/login/test-token")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == "admin@example.com"


def test_post_login_test_token_unauthorized(base_url):
    res = requests.post(f"{base_url}/api/v1/login/test-token")
    assert res.status_code in [401, 403]


# --- Password Recovery & Reset Endpoints ---

def test_post_password_recovery_success(api):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    res = api.post(f"/api/v1/password-recovery/{email}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=SCHEMA_MESSAGE)


def test_post_password_recovery_html_content_success(api):
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    res = api.post(f"/api/v1/password-recovery-html-content/{email}")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert isinstance(res.text, str)


def test_post_password_recovery_html_content_unauthorized(base_url):
    email = "admin@example.com"
    res = requests.post(f"{base_url}/api/v1/password-recovery-html-content/{email}")
    assert res.status_code in [401, 403]


def test_post_reset_password_validation_error(api):
    res = api.post("/api/v1/reset-password/", json={"token": "tok"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_post_reset_password_invalid_token(api):
    payload = {"token": "invalid-token", "new_password": "newpassword123"}
    res = api.post("/api/v1/reset-password/", json=payload)
    assert res.status_code in [200, 400, 404]
    if res.status_code == 200:
        validate(instance=res.json(), schema=SCHEMA_MESSAGE)


# --- Users Endpoints ---

def test_get_users_success(api):
    res = api.get("/api/v1/users/", params={"skip": 0, "limit": 10})
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USERS_PUBLIC)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_users_validation_error(api):
    res = api.get("/api/v1/users/", params={"skip": "invalid_number"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_get_users_unauthorized(base_url):
    res = requests.get(f"{base_url}/api/v1/users/")
    assert res.status_code in [401, 403]


def test_post_users_create_success(api):
    unique_email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "validPassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }
    res = api.post("/api/v1/users/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == unique_email

    # Cleanup
    user_id = data["id"]
    api.delete(f"/api/v1/users/{user_id}")


def test_post_users_create_validation_error(api):
    payload = {"email": "invalid-email-format", "password": "short"}
    res = api.post("/api/v1/users/", json=payload)
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_post_users_signup_success(base_url):
    unique_email = f"signup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "strongPassword123",
        "full_name": "Signup User",
    }
    res = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == unique_email


def test_post_users_signup_validation_error(base_url):
    res = requests.post(f"{base_url}/api/v1/users/signup", json={"email": "bad"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_get_users_me_success(api):
    res = api.get("/api/v1/users/me")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == "admin@example.com"


def test_patch_users_me_validation_error(api):
    res = api.patch("/api/v1/users/me", json={"email": "not-an-email"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_patch_users_me_password_validation_error(api):
    res = api.patch("/api/v1/users/me/password", json={"current_password": "short"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_user_me_flow_update_password_and_delete(base_url):
    unique_email = f"user_lifecycle_{uuid.uuid4().hex[:8]}@example.com"
    old_pwd = "passwordOld123"
    new_pwd = "passwordNew123"

    res_reg = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": unique_email, "password": old_pwd, "full_name": "Lifecycle User"},
    )
    assert res_reg.status_code == 200

    res_tok = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": unique_email, "password": old_pwd},
    )
    token = res_tok.json()["access_token"]
    user_session = requests.Session()
    user_session.headers.update({"Authorization": f"Bearer {token}"})

    # Update own details
    patch_res = user_session.patch(
        f"{base_url}/api/v1/users/me", json={"full_name": "Updated Name"}
    )
    assert patch_res.status_code == 200
    validate(instance=patch_res.json(), schema=SCHEMA_USER_PUBLIC)
    assert patch_res.json()["full_name"] == "Updated Name"

    # Update own password
    pwd_res = user_session.patch(
        f"{base_url}/api/v1/users/me/password",
        json={"current_password": old_pwd, "new_password": new_pwd},
    )
    assert pwd_res.status_code == 200
    validate(instance=pwd_res.json(), schema=SCHEMA_MESSAGE)

    # Delete own user
    del_res = user_session.delete(f"{base_url}/api/v1/users/me")
    assert del_res.status_code == 200
    validate(instance=del_res.json(), schema=SCHEMA_MESSAGE)


def test_get_users_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": f"find_{uuid.uuid4().hex[:8]}@example.com", "password": "password123"},
    )
    user_id = create_res.json()["id"]

    res = api.get(f"/api/v1/users/{user_id}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=SCHEMA_USER_PUBLIC)
    assert res.json()["id"] == user_id

    # Cleanup
    api.delete(f"/api/v1/users/{user_id}")


def test_get_users_by_id_validation_error(api):
    res = api.get("/api/v1/users/invalid-uuid-format")
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_patch_users_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": f"mod_{uuid.uuid4().hex[:8]}@example.com", "password": "password123"},
    )
    user_id = create_res.json()["id"]

    res = api.patch(f"/api/v1/users/{user_id}", json={"full_name": "Modified Name"})
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["full_name"] == "Modified Name"

    # Cleanup
    api.delete(f"/api/v1/users/{user_id}")


def test_patch_users_by_id_validation_error(api):
    random_uuid = str(uuid.uuid4())
    res = api.patch(f"/api/v1/users/{random_uuid}", json={"email": "not-valid-email"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_delete_users_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": f"del_{uuid.uuid4().hex[:8]}@example.com", "password": "password123"},
    )
    user_id = create_res.json()["id"]

    res = api.delete(f"/api/v1/users/{user_id}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=SCHEMA_MESSAGE)


def test_delete_users_by_id_validation_error(api):
    res = api.delete("/api/v1/users/not-a-uuid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


# --- Utils Endpoints ---

def test_get_utils_health_check(api):
    res = api.get("/api/v1/utils/health-check/")
    assert res.status_code == 200
    assert isinstance(res.json(), bool)


def test_post_utils_test_email_success(api):
    res = api.post(
        "/api/v1/utils/test-email/",
        params={"email_to": "admin@example.com"},
    )
    assert res.status_code == 201
    validate(instance=res.json(), schema=SCHEMA_MESSAGE)


def test_post_utils_test_email_validation_error(api):
    res = api.post(
        "/api/v1/utils/test-email/",
        params={"email_to": "not-an-email"},
    )
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


# --- Items Endpoints ---

def test_get_items_success(api):
    res = api.get("/api/v1/items/", params={"skip": 0, "limit": 10})
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_ITEMS_PUBLIC)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_items_validation_error(api):
    res = api.get("/api/v1/items/", params={"limit": "not_an_int"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_post_items_create_success(api):
    payload = {"title": "Test Item", "description": "Item created by regression tests"}
    res = api.post("/api/v1/items/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["title"] == payload["title"]

    # Cleanup
    item_id = data["id"]
    api.delete(f"/api/v1/items/{item_id}")


def test_post_items_create_validation_error(api):
    res = api.post("/api/v1/items/", json={})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_get_items_by_id_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item To Read"})
    item_id = create_res.json()["id"]

    res = api.get(f"/api/v1/items/{item_id}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["id"] == item_id

    # Cleanup
    api.delete(f"/api/v1/items/{item_id}")


def test_get_items_by_id_validation_error(api):
    res = api.get("/api/v1/items/invalid-uuid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


def test_put_items_by_id_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Initial Title"})
    item_id = create_res.json()["id"]

    res = api.put(
        f"/api/v1/items/{item_id}",
        json={"title": "Updated Title", "description": "Updated Description"},
    )
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated Description"

    # Cleanup
    api.delete(f"/api/v1/items/{item_id}")


def test_put_items_by_id_validation_error(api):
    create_res = api.post("/api/v1/items/", json={"title": "To Update Invalid"})
    item_id = create_res.json()["id"]

    res = api.put(f"/api/v1/items/{item_id}", json={"title": ""})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)

    # Cleanup
    api.delete(f"/api/v1/items/{item_id}")


def test_delete_items_by_id_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item To Delete"})
    item_id = create_res.json()["id"]

    res = api.delete(f"/api/v1/items/{item_id}")
    assert res.status_code == 200
    validate(instance=res.json(), schema=SCHEMA_MESSAGE)


def test_delete_items_by_id_validation_error(api):
    res = api.delete("/api/v1/items/not-a-valid-uuid")
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)


# --- Private Endpoints ---

def test_post_private_users_create_success(api):
    unique_email = f"priv_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "privatePassword123",
        "full_name": "Private User",
        "is_verified": True,
    }
    res = api.post("/api/v1/private/users/", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == unique_email

    # Cleanup
    user_id = data["id"]
    api.delete(f"/api/v1/users/{user_id}")


def test_post_private_users_create_validation_error(api):
    res = api.post("/api/v1/private/users/", json={"email": "incomplete-data"})
    assert res.status_code == 422
    validate(instance=res.json(), schema=SCHEMA_VALIDATION_ERROR)
