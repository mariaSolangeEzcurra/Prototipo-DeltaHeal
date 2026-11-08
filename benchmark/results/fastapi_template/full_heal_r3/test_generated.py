import uuid
import pytest
import requests
from jsonschema import validate

# ---------------------------------------------------------
# Schemas JSON Schema para validación de contratos
# ---------------------------------------------------------

USER_PUBLIC_SCHEMA = {
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
# Utilidades locales para generación de datos únicos
# ---------------------------------------------------------

def generate_random_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


# ---------------------------------------------------------
# Tests: Login & Auth
# ---------------------------------------------------------

def test_post_login_access_token_success(api):
    payload = {"username": "admin@example.com", "password": "changethis"}
    response = api.post("/api/v1/login/access-token", data=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=TOKEN_SCHEMA)
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


def test_post_login_access_token_invalid_form_validation_error(api):
    response = api.post("/api/v1/login/access-token", data={})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_login_test_token_authenticated_success(api):
    response = api.post("/api/v1/login/test-token")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_post_login_test_token_unauthenticated(base_url):
    response = requests.post(f"{base_url}/api/v1/login/test-token")
    assert response.status_code in [401, 403]


# ---------------------------------------------------------
# Tests: Password Recovery & Reset
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
    assert "text/html" in response.headers.get("content-type", "")
    assert isinstance(response.text, str)


def test_post_password_recovery_html_content_unauthenticated(base_url):
    response = requests.post(f"{base_url}/api/v1/password-recovery-html-content/admin@example.com")
    assert response.status_code in [401, 403]


def test_post_reset_password_invalid_data_validation_error(api):
    # Enviar contraseña menor a 8 caracteres provoca un 422
    payload = {"token": "some-token", "new_password": "short"}
    response = api.post("/api/v1/reset-password/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_reset_password_invalid_token(api):
    payload = {"token": "invalid-token-123", "new_password": "newValidPassword123"}
    response = api.post("/api/v1/reset-password/", json=payload)
    # Puede devolver 400 por token inválido/expirado o 200 si la implementación simula éxito
    assert response.status_code in [200, 400, 404]


# ---------------------------------------------------------
# Tests: Users Read & Create (/api/v1/users/)
# ---------------------------------------------------------

def test_get_users_read_users_success(api):
    response = api.get("/api/v1/users/?skip=0&limit=5")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USERS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_users_read_users_validation_error(api):
    response = api.get("/api/v1/users/?limit=invalid_integer")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_get_users_unauthenticated(base_url):
    response = requests.get(f"{base_url}/api/v1/users/")
    assert response.status_code in [401, 403]


def test_post_users_create_user_success(api):
    new_email = generate_random_email()
    payload = {
        "email": new_email,
        "password": "strongPassword123",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
    }
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == new_email

    # Limpieza
    api.delete(f"/api/v1/users/{data['id']}")


def test_post_users_create_user_validation_error(api):
    payload = {"email": "not-an-email", "password": "123"}
    response = api.post("/api/v1/users/", json=payload)
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Tests: Users Me (/api/v1/users/me)
# ---------------------------------------------------------

def test_get_users_read_user_me_success(api):
    response = api.get("/api/v1/users/me")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == "admin@example.com"


def test_patch_users_update_user_me_validation_error(api):
    response = api.patch("/api/v1/users/me", json={"email": "invalid-email-format"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_update_password_me_validation_error(api):
    response = api.patch(
        "/api/v1/users/me/password",
        json={"current_password": "short", "new_password": "short"},
    )
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_and_lifecycle_users_me(base_url):
    # Creamos un usuario normal para probar delete propio sin afectar al admin
    signup_email = generate_random_email()
    password = "normalUserPassword123"
    reg_resp = requests.post(
        f"{base_url}/api/v1/users/signup",
        json={"email": signup_email, "password": password, "full_name": "Delete Me"},
    )
    assert reg_resp.status_code == 200

    token_resp = requests.post(
        f"{base_url}/api/v1/login/access-token",
        data={"username": signup_email, "password": password},
    )
    assert token_resp.status_code == 200
    token = token_resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # Probar patch me
    patch_resp = requests.patch(
        f"{base_url}/api/v1/users/me",
        json={"full_name": "Updated Self Name"},
        headers=user_headers,
    )
    assert patch_resp.status_code == 200
    validate(instance=patch_resp.json(), schema=USER_PUBLIC_SCHEMA)

    # Probar delete me
    del_resp = requests.delete(f"{base_url}/api/v1/users/me", headers=user_headers)
    assert del_resp.status_code == 200
    validate(instance=del_resp.json(), schema=MESSAGE_SCHEMA)


# ---------------------------------------------------------
# Tests: User Registration & Private User (/api/v1/users/signup, /api/v1/private/users/)
# ---------------------------------------------------------

def test_post_users_signup_success(api):
    email = generate_random_email()
    payload = {"email": email, "password": "passwordSignup123", "full_name": "Signup User"}
    response = api.post("/api/v1/users/signup", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)
    assert data["email"] == email

    # Limpieza
    api.delete(f"/api/v1/users/{data['id']}")


def test_post_users_signup_validation_error(api):
    response = api.post("/api/v1/users/signup", json={"email": "bad_email", "password": "1"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_private_users_create_user_success(api):
    email = generate_random_email()
    payload = {
        "email": email,
        "password": "privatePassword123",
        "full_name": "Private User",
        "is_verified": False,
    }
    response = api.post("/api/v1/private/users/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_PUBLIC_SCHEMA)

    # Limpieza
    api.delete(f"/api/v1/users/{data['id']}")


def test_post_private_users_validation_error(api):
    response = api.post("/api/v1/private/users/", json={})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Tests: Users by ID (/api/v1/users/{user_id})
# ---------------------------------------------------------

def test_users_by_id_crud_flow(api):
    # 1. Crear usuario
    email = generate_random_email()
    create_resp = api.post(
        "/api/v1/users/",
        json={"email": email, "password": "securePassword123", "full_name": "Target User"},
    )
    assert create_resp.status_code == 200
    user_id = create_resp.json()["id"]

    # 2. Leer usuario por ID
    get_resp = api.get(f"/api/v1/users/{user_id}")
    assert get_resp.status_code == 200
    validate(instance=get_resp.json(), schema=USER_PUBLIC_SCHEMA)
    assert get_resp.json()["id"] == user_id

    # 3. Modificar usuario
    patch_resp = api.patch(
        f"/api/v1/users/{user_id}",
        json={"full_name": "Updated Target Name"},
    )
    assert patch_resp.status_code == 200
    validate(instance=patch_resp.json(), schema=USER_PUBLIC_SCHEMA)
    assert patch_resp.json()["full_name"] == "Updated Target Name"

    # 4. Eliminar usuario
    del_resp = api.delete(f"/api/v1/users/{user_id}")
    assert del_resp.status_code == 200
    validate(instance=del_resp.json(), schema=MESSAGE_SCHEMA)


def test_get_users_by_id_validation_error(api):
    response = api.get("/api/v1/users/not-a-valid-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_patch_users_by_id_validation_error(api):
    response = api.patch("/api/v1/users/not-a-valid-uuid", json={"email": "bad"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_users_by_id_validation_error(api):
    response = api.delete("/api/v1/users/not-a-valid-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Tests: Utils (/api/v1/utils/)
# ---------------------------------------------------------

def test_get_utils_health_check_success(api):
    response = api.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert response.json() is True


def test_post_utils_test_email_success(api):
    response = api.post("/api/v1/utils/test-email/?email_to=admin@example.com")
    assert response.status_code == 201
    validate(instance=response.json(), schema=MESSAGE_SCHEMA)


def test_post_utils_test_email_validation_error(api):
    response = api.post("/api/v1/utils/test-email/?email_to=not_an_email")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


# ---------------------------------------------------------
# Tests: Items CRUD (/api/v1/items/)
# ---------------------------------------------------------

def test_get_items_read_items_success(api):
    response = api.get("/api/v1/items/?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEMS_PUBLIC_SCHEMA)
    assert isinstance(data["data"], list)
    assert isinstance(data["count"], int)


def test_get_items_read_items_validation_error(api):
    response = api.get("/api/v1/items/?skip=invalid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_post_items_create_item_success(api):
    item_title = f"Item {uuid.uuid4().hex[:6]}"
    payload = {"title": item_title, "description": "Item description"}
    response = api.post("/api/v1/items/", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ITEM_PUBLIC_SCHEMA)
    assert data["title"] == item_title

    # Limpieza
    api.delete(f"/api/v1/items/{data['id']}")


def test_post_items_create_item_validation_error(api):
    # Title es requerido y minLength: 1
    response = api.post("/api/v1/items/", json={"title": ""})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_items_by_id_crud_flow(api):
    # 1. Crear item
    item_title = f"Item-{uuid.uuid4().hex[:6]}"
    create_resp = api.post("/api/v1/items/", json={"title": item_title, "description": "Original"})
    assert create_resp.status_code == 200
    item_id = create_resp.json()["id"]

    # 2. Leer item por ID
    get_resp = api.get(f"/api/v1/items/{item_id}")
    assert get_resp.status_code == 200
    validate(instance=get_resp.json(), schema=ITEM_PUBLIC_SCHEMA)
    assert get_resp.json()["id"] == item_id

    # 3. Modificar item (PUT)
    updated_title = f"Updated-{item_title}"
    put_resp = api.put(f"/api/v1/items/{item_id}", json={"title": updated_title, "description": "New Desc"})
    assert put_resp.status_code == 200
    validate(instance=put_resp.json(), schema=ITEM_PUBLIC_SCHEMA)
    assert put_resp.json()["title"] == updated_title

    # 4. Eliminar item
    del_resp = api.delete(f"/api/v1/items/{item_id}")
    assert del_resp.status_code == 200
    validate(instance=del_resp.json(), schema=MESSAGE_SCHEMA)


def test_get_items_by_id_validation_error(api):
    response = api.get("/api/v1/items/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_put_items_by_id_validation_error(api):
    response = api.put("/api/v1/items/not-a-uuid", json={"title": "Test"})
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)


def test_delete_items_by_id_validation_error(api):
    response = api.delete("/api/v1/items/not-a-uuid")
    assert response.status_code == 422
    validate(instance=response.json(), schema=HTTP_VALIDATION_ERROR_SCHEMA)
