import uuid
import pytest
import requests
from jsonschema import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_string(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# GET /createdb
# ---------------------------------------------------------------------------

def test_get_createdb_success(api):
    response = api.get("/createdb")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

def test_get_home_success(api):
    response = api.get("/")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "help": {"type": "string"},
            "vulnerable": {"type": "number"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /users/v1
# ---------------------------------------------------------------------------

def test_get_users_v1_success(api):
    response = api.get("/users/v1")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "required": ["users"],
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "username": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /users/v1/_debug
# ---------------------------------------------------------------------------

def test_get_users_v1_debug_success(api):
    response = api.get("/users/v1/_debug")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "required": ["users"],
        "properties": {
            "users": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "admin": {"type": "boolean"},
                        "email": {"type": "string"},
                        "password": {"type": "string"},
                        "username": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# POST /users/v1/register
# ---------------------------------------------------------------------------

def test_post_users_v1_register_success(api):
    username = random_string("user_")
    payload = {
        "username": username,
        "password": "validPassword123",
        "email": f"{username}@testmail.com"
    }
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=data, schema=schema)


def test_post_users_v1_register_invalid_request(api):
    # Missing required credentials / malformed request
    response = api.post("/users/v1/register", json={})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /users/v1/login
# ---------------------------------------------------------------------------

def test_post_users_v1_login_success(api):
    username = random_string("login_u_")
    password = "secretPassword123"
    api.post("/users/v1/register", json={
        "username": username,
        "password": password,
        "email": f"{username}@testmail.com"
    })

    payload = {"username": username, "password": password}
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "auth_token": {"type": "string"},
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=data, schema=schema)


def test_post_users_v1_login_invalid_credentials(api):
    payload = {
        "username": "admin",
        "password": "wrong_password_xyz"
    }
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 400
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

def test_get_me_success(api):
    response = api.get("/me")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "data": {
                "type": "object",
                "properties": {
                    "admin": {"type": "boolean"},
                    "email": {"type": "string"},
                    "username": {"type": "string"}
                }
            },
            "status": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_get_me_unauthorized(base_url):
    response = requests.get(f"{base_url}/me")
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /users/v1/{username}
# ---------------------------------------------------------------------------

def test_get_user_by_username_success(api):
    username = random_string("get_u_")
    email = f"{username}@testmail.com"
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": email
    })

    response = api.get(f"/users/v1/{username}")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)
    assert data.get("username") == username


def test_get_user_by_username_not_found(api):
    non_existent_user = random_string("nonexistent_")
    response = api.get(f"/users/v1/{non_existent_user}")
    assert response.status_code == 404
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# DELETE /users/v1/{username}
# ---------------------------------------------------------------------------

def test_delete_user_by_username_success(api):
    # Created user to be deleted by admin session
    username = random_string("del_u_")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": f"{username}@testmail.com"
    })

    response = api.delete(f"/users/v1/{username}")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=data, schema=schema)


def test_delete_user_by_username_not_found(api):
    non_existent_user = random_string("ghost_")
    response = api.delete(f"/users/v1/{non_existent_user}")
    assert response.status_code == 404
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_delete_user_by_username_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name1")
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# PUT /users/v1/{username}/email
# ---------------------------------------------------------------------------

def test_put_user_email_success(api):
    username = random_string("email_u_")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": f"{username}@testmail.com"
    })

    new_email = f"updated_{username}@testmail.com"
    response = api.put(f"/users/v1/{username}/email", json={"email": new_email})
    assert response.status_code == 204


def test_put_user_email_invalid_request(api):
    username = random_string("inv_mail_")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": f"{username}@testmail.com"
    })

    response = api.put(f"/users/v1/{username}/email", json={"email": "not-an-email"})
    assert response.status_code == 400
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_put_user_email_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/name1/email",
        json={"email": "unauth@mail.com"}
    )
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# PUT /users/v1/{username}/password
# ---------------------------------------------------------------------------

def test_put_user_password_success(api):
    username = random_string("pass_u_")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": f"{username}@testmail.com"
    })

    response = api.put(
        f"/users/v1/{username}/password",
        json={"password": "newSecurePassword456"}
    )
    assert response.status_code == 204


def test_put_user_password_invalid_request(api):
    username = random_string("bad_pass_")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "passUser123",
        "email": f"{username}@testmail.com"
    })

    response = api.put(f"/users/v1/{username}/password", json={"invalid_field": 123})
    assert response.status_code == 400
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_put_user_password_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/name1/password",
        json={"password": "newPasswordWithoutAuth"}
    )
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /books/v1
# ---------------------------------------------------------------------------

def test_get_books_v1_success(api):
    response = api.get("/books/v1")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "Books": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "book_title": {"type": "string"},
                        "user": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# POST /books/v1
# ---------------------------------------------------------------------------

def test_post_books_v1_success(api):
    book_title = random_string("book_")
    payload = {
        "book_title": book_title,
        "secret": "topSecretInfo"
    }
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=data, schema=schema)


def test_post_books_v1_already_exists(api):
    book_title = random_string("dup_book_")
    payload = {
        "book_title": book_title,
        "secret": "secretData"
    }
    first_res = api.post("/books/v1", json=payload)
    assert first_res.status_code == 200

    response = api.post("/books/v1", json=payload)
    assert response.status_code == 400
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_post_books_v1_unauthorized(base_url):
    response = requests.post(
        f"{base_url}/books/v1",
        json={"book_title": "unauthorizedBook", "secret": "none"}
    )
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


# ---------------------------------------------------------------------------
# GET /books/v1/{book_title}
# ---------------------------------------------------------------------------

def test_get_book_by_title_success(api):
    book_title = random_string("owned_book_")
    secret = "secretContent123"
    create_res = api.post("/books/v1", json={"book_title": book_title, "secret": secret})
    assert create_res.status_code == 200

    response = api.get(f"/books/v1/{book_title}")
    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "book_title": {"type": "string"},
                "owner": {"type": "string"},
                "secret": {"type": "string"}
            }
        }
    }
    validate(instance=data, schema=schema)


def test_get_book_by_title_not_found(api):
    non_existent_book = random_string("nobook_")
    response = api.get(f"/books/v1/{non_existent_book}")
    assert response.status_code == 404
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)


def test_get_book_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")
    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=data, schema=schema)
