import uuid
import pytest
import requests
from jsonschema import validate

# JSON Schemas for response validation
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

SCHEMA_TOKEN = {
    "type": "object",
    "required": ["access_token"],
    "properties": {
        "access_token": {"type": "string"},
        "token_type": {"type": "string"},
    },
}

SCHEMA_HTTP_VALIDATION_ERROR = {
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


def random_email():
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------
# Login & Authentication Tests
# ---------------------------------------------------------

def test_post_login_access_token_success(api):
    payload = {"username": "admin@example.com", "password": "changethis"}
    response = api.post("/api/v1/login/access-token", data=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_TOKEN)


def test_post_login_access_token_invalid_data(api):
    # Missing required 'password' field
    payload = {"username": "admin@example.com"}
    response = api.post("/api/v1/login/access-token", data=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_post_test_token_success(api):
    response = api.post("/api/v1/login/test-token")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == "admin@example.com"


def test_post_test_token_unauthorized(base_url):
    response = requests.post(f"{base_url}/api/v1/login/test-token")
    assert response.status_code in [401, 403]


def test_post_password_recovery_success(api):
    # Tests password recovery request for existing/non-existing email
    email = random_email()
    response = api.post(f"/api/v1/password-recovery/{email}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_MESSAGE)


def test_post_password_recovery_html_content_success(api):
    email = "admin@example.com"
    response = api.post(f"/api/v1/password-recovery-html-content/{email}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("Content-Type", "")
    assert isinstance(response.text, str)


def test_post_reset_password_validation_error(api):
    # Invalid new_password (minLength is 8)
    payload = {"token": "fake-token", "new_password": "short"}
    response = api.post("/api/v1/reset-password/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


# ---------------------------------------------------------
# Users Tests
# ---------------------------------------------------------

def test_get_users_success(api):
    response = api.get("/api/v1/users/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USERS_PUBLIC)


def test_get_users_invalid_query_param(api):
    response = api.get("/api/v1/users/?skip=invalid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_post_users_success(api):
    payload = {
        "email": random_email(),
        "password": "strongPassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == payload["email"]


def test_post_users_validation_error(api):
    # Invalid email format and too short password
    payload = {"email": "not-an-email", "password": "123"}
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_post_users_signup_success(api):
    payload = {
        "email": random_email(),
        "password": "signupPassword123",
        "full_name": "Signup User",
    }
    response = api.post("/api/v1/users/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == payload["email"]


def test_post_users_signup_validation_error(api):
    payload = {"email": "invalid-email", "password": "short"}
    response = api.post("/api/v1/users/signup", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_get_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password1234!"},
    )
    user_id = create_res.json()["id"]

    response = api.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["id"] == user_id


def test_get_user_by_id_invalid_uuid(api):
    response = api.get("/api/v1/users/not-a-valid-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_patch_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password1234!"},
    )
    user_id = create_res.json()["id"]

    update_payload = {"full_name": "Updated Name"}
    response = api.patch(f"/api/v1/users/{user_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["full_name"] == "Updated Name"


def test_patch_user_by_id_validation_error(api):
    user_id = str(uuid.uuid4())
    # Password shorter than 8 characters
    response = api.patch(f"/api/v1/users/{user_id}", json={"password": "123"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_delete_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "Password1234!"},
    )
    user_id = create_res.json()["id"]

    response = api.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_MESSAGE)


def test_delete_user_by_id_invalid_uuid(api):
    response = api.delete("/api/v1/users/invalid-uuid-format")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


# ---------------------------------------------------------
# Current User Me Tests
# ---------------------------------------------------------

def test_get_user_me_success(api):
    response = api.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == "admin@example.com"


def test_patch_user_me_success(api):
    response = api.patch("/api/v1/users/me", json={"full_name": "Initial Admin"})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)


def test_patch_user_me_validation_error(api):
    response = api.patch("/api/v1/users/me", json={"email": "invalid-format"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_patch_user_me_password_validation_error(api):
    payload = {"current_password": "short", "new_password": "short"}
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_delete_user_me_success(base_url):
    # Create an ephemeral user to test self-deletion without destroying the admin user
    email = random_email()
    password = "EphemeralPassword123!"
    reg_res = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": email, "password": password, "full_name": "Delete Me"},
    )
    assert reg_res.status_code == 200

    login_res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    user_session = requests.Session()
    user_session.headers.update({"Authorization": f"Bearer {token}"})

    response = user_session.delete(f"{base_url}/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_MESSAGE)


# ---------------------------------------------------------
# Items Tests
# ---------------------------------------------------------

def test_get_items_success(api):
    response = api.get("/api/v1/items/?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_ITEMS_PUBLIC)


def test_get_items_validation_error(api):
    response = api.get("/api/v1/items/?limit=not-an-int")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_post_item_success(api):
    payload = {"title": "Test Item", "description": "Item description"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]


def test_post_item_validation_error(api):
    # Empty title violates minLength: 1
    payload = {"title": "", "description": "No title item"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_get_item_by_id_success(api):
    create_res = api.post(
        "/api/v1/items/",
        json={"title": "Item to Get", "description": "Details"},
    )
    item_id = create_res.json()["id"]

    response = api.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["id"] == item_id


def test_get_item_by_id_invalid_uuid(api):
    response = api.get("/api/v1/items/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_put_item_success(api):
    create_res = api.post(
        "/api/v1/items/",
        json={"title": "Original Title", "description": "Original Description"},
    )
    item_id = create_res.json()["id"]

    update_payload = {"title": "Updated Title", "description": "Updated Description"}
    response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_ITEM_PUBLIC)
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated Description"


def test_put_item_validation_error(api):
    item_id = str(uuid.uuid4())
    # Title violates minLength: 1
    response = api.put(f"/api/v1/items/{item_id}", json={"title": ""})
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


def test_delete_item_success(api):
    create_res = api.post(
        "/api/v1/items/",
        json={"title": "Item to Delete", "description": "To be removed"},
    )
    item_id = create_res.json()["id"]

    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_MESSAGE)


def test_delete_item_invalid_uuid(api):
    response = api.delete("/api/v1/items/invalid-uuid-id")
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


# ---------------------------------------------------------
# Utils Tests
# ---------------------------------------------------------

def test_get_health_check_success(api):
    response = api.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert isinstance(response.json(), bool)


def test_post_test_email_success(api):
    response = api.post(
        "/api/v1/utils/test-email/",
        params={"email_to": "admin@example.com"},
    )
    assert response.status_code == 201
    data = response.json()
    validate(instance=data, schema=SCHEMA_MESSAGE)


def test_post_test_email_validation_error(api):
    response = api.post(
        "/api/v1/utils/test-email/",
        params={"email_to": "not-an-email"},
    )
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)


# ---------------------------------------------------------
# Private Endpoint Tests
# ---------------------------------------------------------

def test_post_private_user_success(api):
    payload = {
        "email": random_email(),
        "password": "privatePassword123!",
        "full_name": "Private User",
        "is_verified": True,
    }
    response = api.post("/api/v1/private/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=SCHEMA_USER_PUBLIC)
    assert data["email"] == payload["email"]


def test_post_private_user_validation_error(api):
    # Missing required 'password' and 'full_name'
    payload = {"email": random_email()}
    response = api.post("/api/v1/private/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=SCHEMA_HTTP_VALIDATION_ERROR)
