import uuid
import pytest
import requests
from jsonschema import validate

# ---------------------------------------------------------
# Schemas JSON Schema según OpenAPI 3.1
# ---------------------------------------------------------
USER_PUBLIC_SCHEMA = {
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

USERS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {"type": "array", "items": USER_PUBLIC_SCHEMA},
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

ITEMS_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["data", "count"],
    "properties": {
        "data": {"type": "array", "items": ITEM_PUBLIC_SCHEMA},
        "count": {"type": "integer"},
    },
}

TOKEN_SCHEMA = {
    "type": "object",
    "required": ["access_token"],
    "properties": {
        "access_token": {"type": "string"},
        "token_type": {"type": "string"},
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
                    "loc": {"type": "array"},
                    "msg": {"type": "string"},
                    "type": {"type": "string"},
                },
            },
        }
    },
}


# ---------------------------------------------------------
# Operaciones: /api/v1/login/access-token
# ---------------------------------------------------------
def test_post_login_access_token_success(api):
    form_data = {
        "username": "admin@example.com",
        "password": "changethis",
    }
    response = api.post("/api/v1/login/access-token", data=form_data)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=TOKEN_SCHEMA)
    assert data["token_type"] == "bearer"


def test_post_login_access_token_validation_error(api):
    # Faltan credenciales requeridas
    response = api.post("/api/v1/login/access-token", data={})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/login/test-token
# ---------------------------------------------------------
def test_post_login_test_token_success(api):
    response = api.post("/api/v1/login/test-token")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_post_login_test_token_unauthorized(base_url):
    response = requests.post(f"{base_url}/api/v1/login/test-token")
    assert response.status_code in [401, 403]


# ---------------------------------------------------------
# Operaciones: /api/v1/password-recovery/{email}
# ---------------------------------------------------------
def test_post_password_recovery_success(api):
    # Crear usuario previo para recuperar password
    user_email = f"recov_{uuid.uuid4().hex[:8]}@example.com"
    api.post(
        "/api/v1/users/",
        json={"email": user_email, "password": "password1234"},
    )
    response = api.post(f"/api/v1/password-recovery/{user_email}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=MESSAGE_SCHEMA)


def test_post_password_recovery_validation_error(api):
    response = api.post("/api/v1/password-recovery/   ")
    assert response.status_code in [400, 404, 422]
    if response.status_code == 422:
        validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/password-recovery-html-content/{email}
# ---------------------------------------------------------
def test_post_password_recovery_html_content_success(api):
    user_email = f"html_{uuid.uuid4().hex[:8]}@example.com"
    api.post(
        "/api/v1/users/",
        json={"email": user_email, "password": "password1234"},
    )
    response = api.post(f"/api/v1/password-recovery-html-content/{user_email}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert isinstance(response.text, str)


def test_post_password_recovery_html_content_unauthorized(base_url):
    response = requests.post(
        f"{base_url}/api/v1/password-recovery-html-content/test@example.com"
    )
    assert response.status_code in [401, 403]


# ---------------------------------------------------------
# Operaciones: /api/v1/reset-password/
# ---------------------------------------------------------
def test_post_reset_password_validation_error_short_password(api):
    # La contraseña debe tener minLength 8
    payload = {"token": "fake-token", "new_password": "short"}
    response = api.post("/api/v1/reset-password/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_reset_password_validation_error_missing_fields(api):
    response = api.post("/api/v1/reset-password/", json={})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/users/
# ---------------------------------------------------------
def test_get_users_success(api):
    response = api.get("/api/v1/users/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_users_validation_error(api):
    response = api.get("/api/v1/users/?limit=invalid_number")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_unauthorized(base_url):
    response = requests.get(f"{base_url}/api/v1/users/")
    assert response.status_code in [401, 403]


def test_post_users_create_success(api):
    unique_email = f"new_user_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "strongPassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == unique_email
    assert data["full_name"] == "Test User"


def test_post_users_create_validation_error(api):
    # Email inválido y sin password requerida
    payload = {"email": "not-an-email"}
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/users/signup
# ---------------------------------------------------------
def test_post_users_signup_success(base_url):
    unique_email = f"signup_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": unique_email,
        "password": "strongPassword123",
        "full_name": "Registered User",
    }
    response = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == unique_email


def test_post_users_signup_validation_error(base_url):
    payload = {"email": "invalid_email_format", "password": "123"}
    response = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/users/me
# ---------------------------------------------------------
def test_get_users_me_success(api):
    response = api.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_get_users_me_unauthorized(base_url):
    response = requests.get(f"{base_url}/api/v1/users/me")
    assert response.status_code in [401, 403]


def test_patch_users_me_success(api):
    payload = {"full_name": "Updated Admin Name"}
    response = api.patch("/api/v1/users/me", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "Updated Admin Name"


def test_patch_users_me_validation_error(api):
    payload = {"email": "not-a-valid-email"}
    response = api.patch("/api/v1/users/me", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_and_patch_password_users_me_as_dedicated_user(base_url):
    # Probar delete /users/me y patch /users/me/password con un usuario nuevo para no afectar al admin
    user_email = f"me_test_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "originalPassword123"
    reg_resp = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": user_email, "password": pwd},
    )
    assert reg_resp.status_code == 200

    token_resp = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": user_email, "password": pwd},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]
    user_session = requests.Session()
    user_session.headers.update({"Authorization": f"Bearer {token}"})

    # Test patch /users/me/password (success)
    new_pwd = "newPassword456"
    pwd_update_resp = user_session.patch(
        f"{base_url}/api/v1/users/me/password",
        json={"current_password": pwd, "new_password": new_pwd},
    )
    assert pwd_update_resp.status_code == 200
    validate(instance=pwd_update_resp.json(), schema=MESSAGE_SCHEMA)

    # Test patch /users/me/password validation error (pwd < 8 caracteres)
    pwd_val_resp = user_session.patch(
        f"{base_url}/api/v1/users/me/password",
        json={"current_password": new_pwd, "new_password": "short"},
    )
    assert pwd_val_resp.status_code == 422
    validate(instance=pwd_val_resp.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)

    # Test delete /users/me
    del_resp = user_session.delete(f"{base_url}/api/v1/users/me")
    assert del_resp.status_code == 200
    validate(instance=del_resp.json(), schema=MESSAGE_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/users/{user_id}
# ---------------------------------------------------------
def test_get_user_by_id_success(api):
    new_email = f"user_by_id_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = api.post(
        "/api/v1/users/",
        json={"email": new_email, "password": "password1234"},
    )
    assert create_resp.status_code == 200
    user_id = create_resp.json()["id"]

    response = api.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["id"] == user_id


def test_get_user_by_id_validation_error(api):
    response = api.get("/api/v1/users/invalid-uuid-format")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_user_by_id_success(api):
    new_email = f"user_patch_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = api.post(
        "/api/v1/users/",
        json={"email": new_email, "password": "password1234"},
    )
    user_id = create_resp.json()["id"]

    patch_payload = {"full_name": "Updated by Admin"}
    response = api.patch(f"/api/v1/users/{user_id}", json=patch_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "Updated by Admin"


def test_patch_user_by_id_validation_error(api):
    response = api.patch(
        "/api/v1/users/invalid-uuid", json={"email": "valid@example.com"}
    )
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_user_by_id_success(api):
    new_email = f"user_delete_{uuid.uuid4().hex[:8]}@example.com"
    create_resp = api.post(
        "/api/v1/users/",
        json={"email": new_email, "password": "password1234"},
    )
    user_id = create_resp.json()["id"]

    response = api.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_delete_user_by_id_validation_error(api):
    response = api.delete("/api/v1/users/not-a-valid-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/private/users/
# ---------------------------------------------------------
def test_post_private_users_success(api):
    email = f"private_{uuid.uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "password1234",
        "full_name": "Private User",
        "is_verified": True,
    }
    response = api.post("/api/v1/private/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_private_users_validation_error(api):
    # Faltan campos requeridos password y full_name
    response = api.post("/api/v1/private/users/", json={"email": "private@test.com"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/utils/
# ---------------------------------------------------------
def test_get_utils_health_check_success(api):
    response = api.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert response.json() is True


def test_post_utils_test_email_success(api):
    target_email = "recipient@example.com"
    response = api.post(f"/api/v1/utils/test-email/?email_to={target_email}")
    assert response.status_code == 201
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_post_utils_test_email_validation_error(api):
    response = api.post("/api/v1/utils/test-email/?email_to=invalid-email-format")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/items/
# ---------------------------------------------------------
def test_get_items_success(api):
    response = api.get("/api/v1/items/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEMS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_items_validation_error(api):
    response = api.get("/api/v1/items/?skip=not-an-int")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_items_unauthorized(base_url):
    response = requests.get(f"{base_url}/api/v1/items/")
    assert response.status_code in [401, 403]


def test_post_items_create_success(api):
    payload = {
        "title": f"Item_{uuid.uuid4().hex[:6]}",
        "description": "Item description",
    }
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]


def test_post_items_create_validation_error(api):
    # 'title' es obligatorio y minLength: 1
    response = api.post("/api/v1/items/", json={"title": ""})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: /api/v1/items/{id}
# ---------------------------------------------------------
def test_get_item_by_id_success(api):
    create_resp = api.post(
        "/api/v1/items/",
        json={"title": "Item To Fetch", "description": "Fetch test"},
    )
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    response = api.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id


def test_get_item_by_id_validation_error(api):
    response = api.get("/api/v1/items/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_by_id_success(api):
    create_resp = api.post(
        "/api/v1/items/",
        json={"title": "Item To Update", "description": "Original"},
    )
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    update_payload = {"title": "Updated Item Title", "description": "Updated"}
    response = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == "Updated Item Title"


def test_put_item_by_id_validation_error(api):
    response = api.put("/api/v1/items/not-a-valid-uuid", json={"title": "New"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_item_by_id_success(api):
    create_resp = api.post(
        "/api/v1/items/",
        json={"title": "Item To Delete", "description": "Delete test"},
    )
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    response = api.delete(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_delete_item_by_id_validation_error(api):
    response = api.delete("/api/v1/items/non-uuid-string")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)
