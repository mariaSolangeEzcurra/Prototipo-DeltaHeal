import uuid
import pytest
import requests
from jsonschema import validate


def generate_unique_str(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# --- Tests for /createdb ---


def test_get_createdb_success(api):
    res = api.get("/createdb")
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for / ---


def test_get_home_success(api):
    res = api.get("/")
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "help": {"type": "string"},
            "vulnerable": {"type": "number"},
        },
        "required": ["message", "help", "vulnerable"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1 ---


def test_get_users_v1_success(api):
    res = api.get("/users/v1")
    assert res.status_code == 200
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
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/_debug ---


def test_get_users_v1_debug_success(api):
    res = api.get("/users/v1/_debug")
    assert res.status_code == 200
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
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/register ---


def test_post_users_v1_register_success(api):
    uname = generate_unique_str("user")
    payload = {
        "username": uname,
        "password": "validPassword123",
        "email": f"{uname}@example.com",
    }
    res = api.post("/users/v1/register", json=payload)
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["status"] == "success"


def test_post_users_v1_register_bad_request(api):
    # Missing required field or malformed request
    payload = {"username": generate_unique_str("incomplete")}
    res = api.post("/users/v1/register", json=payload)
    assert res.status_code == 400


# --- Tests for /users/v1/login ---


def test_post_users_v1_login_success(api):
    uname = generate_unique_str("login_user")
    pwd = "password123"
    api.post(
        "/users/v1/register",
        json={"username": uname, "password": pwd, "email": f"{uname}@mail.com"},
    )

    res = api.post("/users/v1/login", json={"username": uname, "password": pwd})
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "auth_token": {"type": "string"},
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["auth_token", "message", "status"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["status"] == "success"


def test_post_users_v1_login_bad_request_wrong_password(api):
    res = api.post(
        "/users/v1/login", json={"username": "name1", "password": "wrong_password"}
    )
    assert res.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["status"] == "fail"


# --- Tests for /me ---


def test_get_me_success(api):
    res = api.get("/me")
    assert res.status_code == 200
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
    validate(instance=res.json(), schema=schema)
    assert res.json()["data"]["username"] == "admin"


def test_get_me_unauthorized(base_url):
    res = requests.get(f"{base_url}/me")
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/{username} (GET) ---


def test_get_users_v1_username_success(api):
    res = api.get("/users/v1/name1")
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "username": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["username", "email"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["username"] == "name1"


def test_get_users_v1_username_not_found(api):
    non_existent = generate_unique_str("nonexistent")
    res = api.get(f"/users/v1/{non_existent}")
    assert res.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/{username} (DELETE) ---


def test_delete_users_v1_username_success(api):
    uname = generate_unique_str("to_delete")
    api.post(
        "/users/v1/register",
        json={"username": uname, "password": "pass1", "email": f"{uname}@mail.com"},
    )

    res = api.delete(f"/users/v1/{uname}")
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["status"] == "success"


def test_delete_users_v1_username_unauthorized(base_url):
    res = requests.delete(f"{base_url}/users/v1/name2")
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


def test_delete_users_v1_username_not_found(api):
    non_existent = generate_unique_str("nonexistent_user")
    res = api.delete(f"/users/v1/{non_existent}")
    assert res.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/{username}/email ---


def test_put_users_v1_email_success(api):
    uname = generate_unique_str("user_email")
    api.post(
        "/users/v1/register",
        json={"username": uname, "password": "pass1", "email": f"{uname}@mail.com"},
    )

    new_email = f"updated_{uname}@mail.com"
    res = api.put(f"/users/v1/{uname}/email", json={"email": new_email})
    assert res.status_code == 204


def test_put_users_v1_email_bad_request(api):
    res = api.put("/users/v1/name1/email", json={"email": "invalid-email-address"})
    assert res.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


def test_put_users_v1_email_unauthorized(base_url):
    res = requests.put(
        f"{base_url}/users/v1/name1/email", json={"email": "valid@email.com"}
    )
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /users/v1/{username}/password ---


def test_put_users_v1_password_success(api):
    uname = generate_unique_str("user_pwd")
    api.post(
        "/users/v1/register",
        json={"username": uname, "password": "pass1", "email": f"{uname}@mail.com"},
    )

    res = api.put(f"/users/v1/{uname}/password", json={"password": "new_secret_pass"})
    assert res.status_code == 204


def test_put_users_v1_password_bad_request(api):
    # Malformed data (e.g. invalid json payload or empty object)
    res = api.put("/users/v1/name1/password", json={})
    assert res.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


def test_put_users_v1_password_unauthorized(base_url):
    res = requests.put(
        f"{base_url}/users/v1/name1/password", json={"password": "new_secret_pass"}
    )
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /books/v1 ---


def test_get_books_v1_success(api):
    res = api.get("/books/v1")
    assert res.status_code == 200
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
    validate(instance=res.json(), schema=schema)


def test_post_books_v1_success(api):
    title = generate_unique_str("book")
    payload = {"book_title": title, "secret": "classified_content"}
    res = api.post("/books/v1", json=payload)
    assert res.status_code == 200
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    validate(instance=res.json(), schema=schema)
    assert res.json()["status"] == "success"


def test_post_books_v1_bad_request_already_exists(api):
    title = generate_unique_str("book_duplicate")
    payload = {"book_title": title, "secret": "secret_data"}
    # Create the book first
    first_res = api.post("/books/v1", json=payload)
    assert first_res.status_code == 200

    # Try creating it again
    res = api.post("/books/v1", json=payload)
    assert res.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


def test_post_books_v1_unauthorized(base_url):
    payload = {"book_title": generate_unique_str("unauth_book"), "secret": "hidden"}
    res = requests.post(f"{base_url}/books/v1", json=payload)
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


# --- Tests for /books/v1/{book_title} ---


def test_get_books_v1_title_success(api):
    title = generate_unique_str("my_book")
    secret_text = "super_secret"
    post_res = api.post(
        "/books/v1", json={"book_title": title, "secret": secret_text}
    )
    assert post_res.status_code == 200

    res = api.get(f"/books/v1/{title}")
    assert res.status_code == 200
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
    validate(instance=res.json(), schema=schema)
    assert len(res.json()) > 0
    assert res.json()[0]["book_title"] == title


def test_get_books_v1_title_not_found(api):
    non_existent = generate_unique_str("missing_book")
    res = api.get(f"/books/v1/{non_existent}")
    assert res.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)


def test_get_books_v1_title_unauthorized(base_url):
    res = requests.get(f"{base_url}/books/v1/bookTitle1")
    assert res.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    validate(instance=res.json(), schema=schema)
