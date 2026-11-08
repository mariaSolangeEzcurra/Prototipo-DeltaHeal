import uuid
import pytest
import requests
from jsonschema import validate


# Helper functions
def generate_unique_str(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# -----------------------------------------------------------------------------
# Endpoint: /createdb
# -----------------------------------------------------------------------------
def test_get_createdb_success(api):
    response = api.get("/createdb")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /
# -----------------------------------------------------------------------------
def test_get_home_success(api):
    response = api.get("/")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "help": {"type": "string"},
            "vulnerable": {"type": "number"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1
# -----------------------------------------------------------------------------
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
                        "username": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/_debug
# -----------------------------------------------------------------------------
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
                        "username": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/register
# -----------------------------------------------------------------------------
def test_post_users_v1_register_success(api):
    username = generate_unique_str("reguser")
    payload = {
        "username": username,
        "password": "Password123!",
        "email": f"{username}@testmail.com"
    }
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["status"] == "success"


def test_post_users_v1_register_invalid_request(api):
    # Missing required fields like password/email
    payload = {"username": generate_unique_str("incomplete")}
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 400


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/login
# -----------------------------------------------------------------------------
def test_post_users_v1_login_success(api):
    payload = {
        "username": "name1",
        "password": "pass1"
    }
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "auth_token": {"type": "string"},
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["status"] == "success"


def test_post_users_v1_login_invalid_credentials(api):
    payload = {
        "username": "name1",
        "password": "WrongPassword999!"
    }
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["status"] == "fail"


# -----------------------------------------------------------------------------
# Endpoint: /me
# -----------------------------------------------------------------------------
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
                    "username": {"type": "string"}
                }
            },
            "status": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_get_me_unauthorized(base_url):
    response = requests.get(f"{base_url}/me")
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/{username} (GET)
# -----------------------------------------------------------------------------
def test_get_users_v1_by_username_success(api):
    response = api.get("/users/v1/name1")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["username"] == "name1"


def test_get_users_v1_by_username_not_found(api):
    non_existent = generate_unique_str("nouser")
    response = api.get(f"/users/v1/{non_existent}")
    assert response.status_code == 404

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/{username} (DELETE)
# -----------------------------------------------------------------------------
def test_delete_users_v1_by_username_success(api):
    # Register a new user first to safely delete it
    username = generate_unique_str("deluser")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "password",
        "email": f"{username}@testmail.com"
    })

    response = api.delete(f"/users/v1/{username}")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["status"] == "success"


def test_delete_users_v1_by_username_not_found(api):
    non_existent = generate_unique_str("nouser")
    response = api.delete(f"/users/v1/{non_existent}")
    assert response.status_code == 404

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_delete_users_v1_by_username_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name1")
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/{username}/email (PUT)
# -----------------------------------------------------------------------------
def test_put_users_v1_email_success(api):
    username = generate_unique_str("emluser")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "password",
        "email": f"{username}@testmail.com"
    })

    new_email = f"updated_{username}@testmail.com"
    response = api.put(f"/users/v1/{username}/email", json={"email": new_email})
    assert response.status_code == 204


def test_put_users_v1_email_invalid_request(api):
    username = generate_unique_str("emluser")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "password",
        "email": f"{username}@testmail.com"
    })

    response = api.put(f"/users/v1/{username}/email", json={"email": "not-a-valid-email"})
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_put_users_v1_email_unauthorized(base_url):
    response = requests.put(f"{base_url}/users/v1/name1/email", json={"email": "new@mail.com"})
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /users/v1/{username}/password (PUT)
# -----------------------------------------------------------------------------
def test_put_users_v1_password_success(api):
    username = generate_unique_str("pwduser")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "password",
        "email": f"{username}@testmail.com"
    })

    response = api.put(f"/users/v1/{username}/password", json={"password": "NewSecretPassword!"})
    assert response.status_code == 204


def test_put_users_v1_password_invalid_request(api):
    username = generate_unique_str("pwduser")
    api.post("/users/v1/register", json={
        "username": username,
        "password": "password",
        "email": f"{username}@testmail.com"
    })

    # Sending invalid/malformed payload
    response = api.put(f"/users/v1/{username}/password", json={"invalid_field": 12345})
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_put_users_v1_password_unauthorized(base_url):
    response = requests.put(f"{base_url}/users/v1/name1/password", json={"password": "newpass"})
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /books/v1 (GET)
# -----------------------------------------------------------------------------
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
                        "user": {"type": "string"}
                    }
                }
            }
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /books/v1 (POST)
# -----------------------------------------------------------------------------
def test_post_books_v1_success(api):
    book_title = generate_unique_str("book")
    payload = {
        "book_title": book_title,
        "secret": "top-secret-content"
    }
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        }
    }
    validate(instance=response.json(), schema=schema)
    assert response.json()["status"] == "success"


def test_post_books_v1_already_exists(api):
    book_title = generate_unique_str("book_dup")
    payload = {
        "book_title": book_title,
        "secret": "original_secret"
    }
    # Create the book first
    first_res = api.post("/books/v1", json=payload)
    assert first_res.status_code == 200

    # Attempt to create duplicate
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_post_books_v1_unauthorized(base_url):
    payload = {
        "book_title": generate_unique_str("unauth_book"),
        "secret": "secret"
    }
    response = requests.post(f"{base_url}/books/v1", json=payload)
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


# -----------------------------------------------------------------------------
# Endpoint: /books/v1/{book_title} (GET)
# -----------------------------------------------------------------------------
def test_get_books_v1_by_title_success(api):
    book_title = generate_unique_str("book_get")
    api.post("/books/v1", json={
        "book_title": book_title,
        "secret": "owner_secret"
    })

    response = api.get(f"/books/v1/{book_title}")
    assert response.status_code == 200

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
    validate(instance=response.json(), schema=schema)
    assert len(response.json()) > 0
    assert response.json()[0]["book_title"] == book_title


def test_get_books_v1_by_title_not_found(api):
    non_existent = generate_unique_str("nobook")
    response = api.get(f"/books/v1/{non_existent}")
    assert response.status_code == 404

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)


def test_get_books_v1_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        }
    }
    validate(instance=response.json(), schema=schema)
