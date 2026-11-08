import uuid
import requests
import pytest
from jsonschema import validate


# Helper function to generate unique identifiers
def unique_str(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Path: /createdb
# ---------------------------------------------------------------------------


def test_get_createdb_success(api):
    response = api.get("/createdb")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /
# ---------------------------------------------------------------------------


def test_get_home_success(api):
    response = api.get("/")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "help": {"type": "string"},
            "vulnerable": {"type": "number"},
        },
        "required": ["message"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1
# ---------------------------------------------------------------------------


def test_get_users_v1_success(api):
    response = api.get("/users/v1")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "username": {"type": "string"},
                    },
                    "required": ["email", "username"],
                },
            }
        },
        "required": ["users"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1/_debug
# ---------------------------------------------------------------------------


def test_get_users_v1_debug_success(api):
    response = api.get("/users/v1/_debug")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "admin": {"type": "boolean"},
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "username": {"type": "string"},
                    },
                    "required": ["admin", "email", "password", "username"],
                },
            }
        },
        "required": ["users"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1/register
# ---------------------------------------------------------------------------


def test_post_users_v1_register_success(api):
    new_user = unique_str("user_")
    payload = {
        "username": new_user,
        "password": "ValidPassword123!",
        "email": f"{new_user}@example.com",
    }
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_post_users_v1_register_bad_request(api):
    # Invalid registration request (missing password and email)
    payload = {"username": unique_str("user_")}
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Path: /users/v1/login
# ---------------------------------------------------------------------------


def test_post_users_v1_login_success(api):
    # Use existing user name1/pass1
    payload = {"username": "name1", "password": "pass1"}
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "auth_token": {"type": "string"},
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["auth_token", "message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_post_users_v1_login_bad_request(api):
    payload = {"username": "name1", "password": "wrong_password"}
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /me
# ---------------------------------------------------------------------------


def test_get_me_success(api):
    response = api.get("/me")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "admin": {"type": "boolean"},
                    "email": {"type": "string"},
                    "username": {"type": "string"},
                },
                "required": ["admin", "email", "username"],
            },
            "status": {"type": "string"},
        },
        "required": ["data", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_get_me_unauthorized(base_url):
    response = requests.get(f"{base_url}/me")
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "enum": [
                    "Signature expired. Please log in again.",
                    "Invalid token. Please log in again.",
                ],
            },
            "status": {"type": "string"},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1/{username}
# ---------------------------------------------------------------------------


def test_get_user_by_username_success(api):
    response = api.get("/users/v1/name1")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["username", "email"],
    }
    validate(instance=response.json(), schema=schema)


def test_get_user_by_username_not_found(api):
    non_existent = unique_str("nouser_")
    response = api.get(f"/users/v1/{non_existent}")
    assert response.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_delete_user_by_username_success(api):
    # Create user first to avoid side effects on fixed users
    user_to_delete = unique_str("deluser_")
    reg_payload = {
        "username": user_to_delete,
        "password": "password123",
        "email": f"{user_to_delete}@test.com",
    }
    create_res = api.post("/users/v1/register", json=reg_payload)
    assert create_res.status_code == 200

    # api fixture is admin, so delete should succeed
    response = api.delete(f"/users/v1/{user_to_delete}")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_delete_user_by_username_not_found(api):
    non_existent = unique_str("nouser_")
    response = api.delete(f"/users/v1/{non_existent}")
    assert response.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_delete_user_by_username_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name2")
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1/{username}/email
# ---------------------------------------------------------------------------


def test_put_user_email_success(api):
    target_user = unique_str("mailuser_")
    api.post(
        "/users/v1/register",
        json={
            "username": target_user,
            "password": "password123",
            "email": f"{target_user}@test.com",
        },
    )

    new_email = f"updated_{target_user}@test.com"
    response = api.put(
        f"/users/v1/{target_user}/email", json={"email": new_email}
    )
    assert response.status_code == 204


def test_put_user_email_bad_request(api):
    target_user = unique_str("mailuser_")
    api.post(
        "/users/v1/register",
        json={
            "username": target_user,
            "password": "password123",
            "email": f"{target_user}@test.com",
        },
    )

    # Invalid email format
    response = api.put(
        f"/users/v1/{target_user}/email", json={"email": "invalid-email"}
    )
    assert response.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_put_user_email_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/name1/email", json={"email": "test@domain.com"}
    )
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /users/v1/{username}/password
# ---------------------------------------------------------------------------


def test_put_user_password_success(api):
    target_user = unique_str("pwduser_")
    api.post(
        "/users/v1/register",
        json={
            "username": target_user,
            "password": "password123",
            "email": f"{target_user}@test.com",
        },
    )

    response = api.put(
        f"/users/v1/{target_user}/password", json={"password": "newPassword456!"}
    )
    assert response.status_code == 204


def test_put_user_password_bad_request(api):
    target_user = unique_str("pwduser_")
    api.post(
        "/users/v1/register",
        json={
            "username": target_user,
            "password": "password123",
            "email": f"{target_user}@test.com",
        },
    )

    # Malformed data (missing password key)
    response = api.put(f"/users/v1/{target_user}/password", json={})
    assert response.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_put_user_password_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/name1/password", json={"password": "newpass"}
    )
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /books/v1
# ---------------------------------------------------------------------------


def test_get_books_v1_success(api):
    response = api.get("/books/v1")
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "Books": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "book_title": {"type": "string"},
                        "user": {"type": "string"},
                    },
                    "required": ["book_title", "user"],
                },
            }
        },
        "required": ["Books"],
    }
    validate(instance=response.json(), schema=schema)


def test_post_books_v1_success(api):
    book_title = unique_str("book_")
    payload = {"book_title": book_title, "secret": "super_secret_text"}
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_post_books_v1_duplicate_bad_request(api):
    book_title = unique_str("book_dup_")
    payload = {"book_title": book_title, "secret": "secret_content"}

    # First creation
    res1 = api.post("/books/v1", json=payload)
    assert res1.status_code == 200

    # Second creation with identical title
    res2 = api.post("/books/v1", json=payload)
    assert res2.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response2 := res2.json(), schema=schema)


def test_post_books_v1_unauthorized(base_url):
    payload = {"book_title": unique_str("book_"), "secret": "secret"}
    response = requests.post(f"{base_url}/books/v1", json=payload)
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


# ---------------------------------------------------------------------------
# Path: /books/v1/{book_title}
# -------------------------------------------


def test_get_book_by_title_success(api):
    # Admin creates a book to ensure ownership
    book_title = unique_str("book_own_")
    create_res = api.post(
        "/books/v1", json={"book_title": book_title, "secret": "admin_secret"}
    )
    assert create_res.status_code == 200

    response = api.get(f"/books/v1/{book_title}")
    assert response.status_code == 200
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "book_title": {"type": "string"},
                "owner": {"type": "string"},
                "secret": {"type": "string"},
            },
            "required": ["book_title", "owner", "secret"],
        },
    }
    validate(instance=response.json(), schema=schema)


def test_get_book_by_title_not_found(api):
    non_existent_title = unique_str("nobook_")
    response = api.get(f"/books/v1/{non_existent_title}")
    assert response.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)


def test_get_book_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")
    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=response.json(), schema=schema)
