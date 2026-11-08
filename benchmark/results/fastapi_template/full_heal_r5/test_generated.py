import uuid
import pytest
import requests
from jsonschema import validate

# ---------------------------------------------------------
# Schemas JSON extraídos del contrato OpenAPI
# ---------------------------------------------------------
USER_PUBLIC_SCHEMA = {
    "type": "object",
    "required": ["email", "id"],
    "properties": {
        "email": {"type": "string"},
        "is_active": {"type": "boolean"},
        "is_superuser": {"type": "boolean"},
        "full_name": {"type": ["string", "null"]},
        "id": {"type": "string", "format": "uuid"},
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
        "id": {"type": "string", "format": "uuid"},
        "owner_id": {"type": "string", "format": "uuid"},
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
                    "input": {},
                    "ctx": {"type": "object"},
                },
            },
        }
    },
}


def random_email():
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------
# Operaciones: Login y Autenticación
# ---------------------------------------------------------

def test_post_login_access_token_success(base_url):
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com", "password": "changethis"},
    )
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=TOKEN_SCHEMA)
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_post_login_access_token_validation_error(base_url):
    response = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": "admin@example.com"},  # Falta password requerido
    )
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_login_test_token_success(api):
    response = api.post("/api/v1/login/test-token")
    assert response.status_code == 200
    validate(instance=response.json(), schema=USER_PUBLIC_SCHEMA)
    assert response.json()["email"] == "admin@example.com"


def test_post_login_test_token_unauthorized(base_url):
    response = requests.post(f"{base_url}/api/v1/login/test-token")
    assert response.status_code in (401, 403)


# ---------------------------------------------------------
# Operaciones: Password Recovery y Reset
# ---------------------------------------------------------

def test_post_password_recovery_success(api):
    email = "admin@example.com"
    response = api.post(f"/api/v1/password-recovery/{email}")
    assert response.status_code == 200
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_post_password_recovery_html_content_success(api):
    email = "admin@example.com"
    response = api.post(f"/api/v1/password-recovery-html-content/{email}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("Content-Type", "")
    assert isinstance(response.text, str)


def test_post_password_recovery_html_content_unauthorized(base_url):
    email = "admin@example.com"
    response = requests.post(f"{base_url}/api/v1/password-recovery-html-content/{email}")
    assert response.status_code in (401, 403)


def test_post_reset_password_validation_error(api):
    # 'new_password' con longitud menor a la requerida (minLength: 8)
    payload = {"token": "dummy-token", "new_password": "short"}
    response = api.post("/api/v1/reset-password/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: Users
# ---------------------------------------------------------

def test_get_users_success(api):
    response = api.get("/api/v1/users/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_users_validation_error(api):
    response = api.get("/api/v1/users/", params={"limit": "not_an_int"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_unauthorized(base_url):
    response = requests.get(f"{base_url}/api/v1/users/")
    assert response.status_code in (401, 403)


def test_post_users_create_success(api):
    email = random_email()
    payload = {
        "email": email,
        "password": "strongPassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email

    # Limpieza
    api.delete(f"/api/v1/users/{data['id']}")


def test_post_users_create_validation_error(api):
    # Contraseña corta y falta email
    payload = {"password": "123"}
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_users_signup_success(base_url):
    email = random_email()
    payload = {
        "email": email,
        "password": "validPassword123",
        "full_name": "Signup User",
    }
    response = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_users_signup_validation_error(base_url):
    payload = {"email": "invalid-email-format", "password": "123"}
    response = requests.post(f"{base_url}/api/v1/users/signup", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_user_me_success(api):
    response = api.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_patch_user_me_success(api):
    response = api.patch("/api/v1/users/me", json={"full_name": "Initial Super User"})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "Initial Super User"


def test_patch_user_me_validation_error(api):
    response = api.patch("/api/v1/users/me", json={"email": "not-valid-email"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_user_me_password_validation_error(api):
    # Contraseña demasiado corta (minLength: 8)
    payload = {"current_password": "short", "new_password": "short"}
    response = api.patch("/api/v1/users/me/password", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_user_me_scenario(base_url):
    # Registramos un usuario efímero para probar el endpoint DELETE /users/me sin borrar al admin
    email = random_email()
    password = "ephemeralPassword123"
    reg_res = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": email, "password": password, "full_name": "Ephemeral User"},
    )
    assert reg_res.status_code == 200

    # Iniciar sesión con este nuevo usuario
    login_res = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # Eliminar el propio usuario
    del_res = session.delete(f"{base_url}/api/v1/users/me")
    assert del_res.status_code == 200
    validate(instance=del_res.json(), schema=MESSAGE_SCHEMA)


def test_get_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "password123", "full_name": "To Read"},
    )
    assert create_res.status_code == 200
    user_id = create_res.json()["id"]

    response = api.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    validate(instance=response.json(), schema=USER_PUBLIC_SCHEMA)
    assert response.json()["id"] == user_id

    # Limpieza
    api.delete(f"/api/v1/users/{user_id}")


def test_get_user_by_id_validation_error(api):
    response = api.get("/api/v1/users/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "password123", "full_name": "Before Update"},
    )
    assert create_res.status_code == 200
    user_id = create_res.json()["id"]

    patch_res = api.patch(f"/api/v1/users/{user_id}", json={"full_name": "After Update"})
    assert patch_res.status_code == 200
    data = patch_res.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["full_name"] == "After Update"

    # Limpieza
    api.delete(f"/api/v1/users/{user_id}")


def test_delete_user_by_id_success(api):
    create_res = api.post(
        "/api/v1/users/",
        json={"email": random_email(), "password": "password123", "full_name": "To Delete"},
    )
    assert create_res.status_code == 200
    user_id = create_res.json()["id"]

    del_res = api.delete(f"/api/v1/users/{user_id}")
    assert del_res.status_code == 200
    validate(instance=del_res.json(), schema=MESSAGE_SCHEMA)


# ---------------------------------------------------------
# Operaciones: Utils
# ---------------------------------------------------------

def test_get_health_check_success(api):
    response = api.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert response.json() is True


def test_post_test_email_success(api):
    response = api.post("/api/v1/utils/test-email/", params={"email_to": "admin@example.com"})
    assert response.status_code == 201
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_post_test_email_validation_error(api):
    response = api.post("/api/v1/utils/test-email/", params={"email_to": "not-an-email"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: Items
# ---------------------------------------------------------

def test_get_items_success(api):
    response = api.get("/api/v1/items/", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEMS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_items_validation_error(api):
    response = api.get("/api/v1/items/", params={"skip": "invalid_int"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_create_success(api):
    payload = {"title": "Test Item Title", "description": "Item Description"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == payload["title"]

    # Limpieza
    api.delete(f"/api/v1/items/{data['id']}")


def test_post_items_create_validation_error(api):
    # 'title' es campo obligatorio
    payload = {"description": "Missing title"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_item_by_id_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Unique Item"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    response = api.get(f"/api/v1/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["id"] == item_id

    # Limpieza
    api.delete(f"/api/v1/items/{item_id}")


def test_get_item_by_id_validation_error(api):
    response = api.get("/api/v1/items/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_item_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Pre-Update Item"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    update_payload = {"title": "Post-Update Item", "description": "Updated desc"}
    update_res = api.put(f"/api/v1/items/{item_id}", json=update_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == update_payload["title"]
    assert data["description"] == update_payload["description"]

    # Limpieza
    api.delete(f"/api/v1/items/{item_id}")


def test_put_item_validation_error(api):
    response = api.put("/api/v1/items/not-a-uuid", json={"title": "Test"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_item_success(api):
    create_res = api.post("/api/v1/items/", json={"title": "Item To Delete"})
    assert create_res.status_code == 200
    item_id = create_res.json()["id"]

    del_res = api.delete(f"/api/v1/items/{item_id}")
    assert del_res.status_code == 200
    validate(instance=del_res.json(), schema=MESSAGE_SCHEMA)


def test_delete_item_validation_error(api):
    response = api.delete("/api/v1/items/not-a-valid-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Operaciones: Private Users
# ---------------------------------------------------------

def test_post_private_users_create_success(base_url):
    email = random_email()
    payload = {
        "email": email,
        "password": "privatePassword123",
        "full_name": "Private User",
        "is_verified": True,
    }
    response = requests.post(f"{base_url}/api/v1/private/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email


def test_post_private_users_create_validation_error(base_url):
    # Falta 'password' y 'full_name' requeridos
    payload = {"email": random_email()}
    response = requests.post(f"{base_url}/api/v1/private/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)
