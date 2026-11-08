import uuid
import pytest
import requests
from jsonschema import validate


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

CREATEDB_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"}
    },
    "required": ["message"]
}

HOME_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "help": {"type": "string"},
        "vulnerable": {"type": "number"}
    },
    "required": ["message", "help", "vulnerable"]
}

USERS_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "users": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "username": {"type": "string"}
                },
                "required": ["email", "username"]
            }
        }
    },
    "required": ["users"]
}

USERS_DEBUG_SCHEMA = {
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
                },
                "required": ["admin", "email", "password", "username"]
            }
        }
    },
    "required": ["users"]
}

USER_REGISTER_200_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "status": {"type": "string", "enum": ["success", "fail"]}
    },
    "required": ["message", "status"]
}

USER_LOGIN_200_SCHEMA = {
    "type": "object",
    "properties": {
        "auth_token": {"type": "string"},
        "message": {"type": "string"},
        "status": {"type": "string", "enum": ["success", "fail"]}
    },
    "required": ["auth_token", "message", "status"]
}

USER_LOGIN_400_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["fail"]},
        "message": {"type": "string"}
    },
    "required": ["status", "message"]
}

ME_200_SCHEMA = {
    "type": "object",
    "properties": {
        "data": {
            "type": "object",
            "properties": {
                "admin": {"type": "boolean"},
                "email": {"type": "string"},
                "username": {"type": "string"}
            },
            "required": ["admin", "email", "username"]
        },
        "status": {"type": "string"}
    },
    "required": ["data", "status"]
}

ME_401_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["fail"]},
        "message": {"type": "string"}
    },
    "required": ["status", "message"]
}

USER_BY_NAME_200_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {"type": "string"},
        "email": {"type": "string"}
    },
    "required": ["username", "email"]
}

GENERIC_FAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["fail"]},
        "message": {"type": "string"}
    },
    "required": ["status", "message"]
}

DELETE_USER_200_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "status": {"type": "string", "enum": ["success", "fail"]}
    },
    "required": ["message", "status"]
}

BOOKS_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "Books": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "book_title": {"type": "string"},
                    "user": {"type": "string"}
                },
                "required": ["book_title", "user"]
            }
        }
    },
    "required": ["Books"]
}

ADD_BOOK_200_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "status": {"type": "string", "enum": ["success", "fail"]}
    },
    "required": ["message", "status"]
}

BOOK_BY_TITLE_200_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "book_title": {"type": "string"},
            "owner": {"type": "string"},
            "secret": {"type": "string"}
        },
        "required": ["book_title", "owner", "secret"]
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_string(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Tests: DB & Home
# ---------------------------------------------------------------------------

def test_get_createdb_success(api):
    response = api.get("/createdb")
    assert response.status_code == 200
    validate(instance=response.json(), schema=CREATEDB_SCHEMA)


def test_get_home_success(api):
    response = api.get("/")
    assert response.status_code == 200
    validate(instance=response.json(), schema=HOME_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: Users Read
# ---------------------------------------------------------------------------

def test_get_users_v1_success(api):
    response = api.get("/users/v1")
    assert response.status_code == 200
    validate(instance=response.json(), schema=USERS_LIST_SCHEMA)


def test_get_users_v1_debug_success(api):
    response = api.get("/users/v1/_debug")
    assert response.status_code == 200
    validate(instance=response.json(), schema=USERS_DEBUG_SCHEMA)


# ---------------------------------------------------------------------------
# Tests: Auth & Registration
# ---------------------------------------------------------------------------

def test_post_users_v1_register_success(api):
    unique_user = random_string("user_")
    payload = {
        "username": unique_user,
        "password": "ValidPassword123!",
        "email": f"{unique_user}@example.com"
    }
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 200
    validate(instance=response.json(), schema=USER_REGISTER_200_SCHEMA)
    assert response.json()["status"] == "success"


def test_post_users_v1_register_bad_request_existing_user(api):
    # 'name1' already exists in the environment
    payload = {
        "username": "name1",
        "password": "password123",
        "email": "name1_dup@example.com"
    }
    response = api.post("/users/v1/register", json=payload)
    assert response.status_code == 400


def test_post_users_v1_login_success(api):
    payload = {
        "username": "name1",
        "password": "pass1"
    }
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 200
    validate(instance=response.json(), schema=USER_LOGIN_200_SCHEMA)
    assert response.json()["status"] == "success"


def test_post_users_v1_login_invalid_password_returns_400(api):
    payload = {
        "username": "name1",
        "password": "incorrect_password"
    }
    response = api.post("/users/v1/login", json=payload)
    assert response.status_code == 400
    validate(instance=response.json(), schema=USER_LOGIN_400_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /me
# ---------------------------------------------------------------------------

def test_get_me_success(api):
    response = api.get("/me")
    assert response.status_code == 200
    validate(instance=response.json(), schema=ME_200_SCHEMA)
    assert response.json()["status"] == "success"


def test_get_me_unauthorized(base_url):
    response = requests.get(f"{base_url}/me")
    assert response.status_code == 401
    validate(instance=response.json(), schema=ME_401_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /users/v1/{username}
# ---------------------------------------------------------------------------

def test_get_users_v1_by_username_success(api):
    response = api.get("/users/v1/name1")
    assert response.status_code == 200
    validate(instance=response.json(), schema=USER_BY_NAME_200_SCHEMA)
    assert response.json()["username"] == "name1"


def test_get_users_v1_by_username_not_found(api):
    non_existent = random_string("nonexistent_")
    response = api.get(f"/users/v1/{non_existent}")
    assert response.status_code == 404
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


def test_delete_users_v1_by_username_success(api):
    # Register a new user to delete
    username_to_del = random_string("todel_")
    reg_resp = api.post("/users/v1/register", json={
        "username": username_to_del,
        "password": "password123",
        "email": f"{username_to_del}@example.com"
    })
    assert reg_resp.status_code == 200

    # API session is admin; should successfully delete
    del_resp = api.delete(f"/users/v1/{username_to_del}")
    assert del_resp.status_code == 200
    validate(instance=del_resp.json(), schema=DELETE_USER_200_SCHEMA)


def test_delete_users_v1_by_username_not_found(api):
    non_existent = random_string("nouser_")
    response = api.delete(f"/users/v1/{non_existent}")
    assert response.status_code == 404
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


def test_delete_users_v1_by_username_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name2")
    assert response.status_code == 401
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /users/v1/{username}/email
# ---------------------------------------------------------------------------

def test_put_users_v1_email_success(api):
    unique_user = random_string("user_")
    api.post("/users/v1/register", json={
        "username": unique_user,
        "password": "password123",
        "email": f"{unique_user}@example.com"
    })
    new_email = f"updated_{unique_user}@example.com"
    response = api.put(f"/users/v1/{unique_user}/email", json={"email": new_email})
    assert response.status_code == 204


def test_put_users_v1_email_invalid_email_returns_400(api):
    response = api.put("/users/v1/admin/email", json={"email": "invalid-email-format"})
    assert response.status_code == 400
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


def test_put_users_v1_email_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/admin/email",
        json={"email": "unauth@example.com"}
    )
    assert response.status_code == 401
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /users/v1/{username}/password
# ---------------------------------------------------------------------------

def test_put_users_v1_password_success(api):
    unique_user = random_string("user_")
    api.post("/users/v1/register", json={
        "username": unique_user,
        "password": "initialPassword1",
        "email": f"{unique_user}@example.com"
    })
    response = api.put(f"/users/v1/{unique_user}/password", json={"password": "newPassword123!"})
    assert response.status_code == 204


def test_put_users_v1_password_malformed_returns_400(api):
    # Sending payload with invalid field name to trigger malformed data error
    response = api.put("/users/v1/admin/password", json={"wrong_key": "somevalue"})
    assert response.status_code == 400
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


def test_put_users_v1_password_unauthorized(base_url):
    response = requests.put(
        f"{base_url}/users/v1/admin/password",
        json={"password": "newpass"}
    )
    assert response.status_code == 401
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /books/v1
# ---------------------------------------------------------------------------

def test_get_books_v1_success(api):
    response = api.get("/books/v1")
    assert response.status_code == 200
    validate(instance=response.json(), schema=BOOKS_LIST_SCHEMA)


def test_post_books_v1_success(api):
    unique_book = random_string("book_")
    payload = {
        "book_title": unique_book,
        "secret": "top_secret_content"
    }
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 200
    validate(instance=response.json(), schema=ADD_BOOK_200_SCHEMA)
    assert response.json()["status"] == "success"


def test_post_books_v1_duplicate_title_returns_400(api):
    unique_book = random_string("book_")
    payload = {
        "book_title": unique_book,
        "secret": "content1"
    }
    # Create the book first
    first_resp = api.post("/books/v1", json=payload)
    assert first_resp.status_code == 200

    # Try creating the duplicate
    second_resp = api.post("/books/v1", json=payload)
    assert second_resp.status_code == 400
    validate(instance=second_resp.json(), schema=GENERIC_FAIL_SCHEMA)
    assert second_resp.json()["status"] == "fail"


def test_post_books_v1_unauthorized(base_url):
    response = requests.post(
        f"{base_url}/books/v1",
        json={"book_title": "unauth_book", "secret": "sec"}
    )
    assert response.status_code == 401
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests: /books/v1/{book_title}
# ---------------------------------------------------------------------------

def test_get_books_v1_by_title_success(api):
    unique_book = random_string("book_")
    secret = "owner_secret_data"
    create_resp = api.post("/books/v1", json={"book_title": unique_book, "secret": secret})
    assert create_resp.status_code == 200

    response = api.get(f"/books/v1/{unique_book}")
    assert response.status_code == 200
    validate(instance=response.json(), schema=BOOK_BY_TITLE_200_SCHEMA)
    assert len(response.json()) > 0
    assert response.json()[0]["book_title"] == unique_book


def test_get_books_v1_by_title_not_found(api):
    non_existent_book = random_string("nobook_")
    response = api.get(f"/books/v1/{non_existent_book}")
    assert response.status_code == 404
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"


def test_get_books_v1_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/any_book")
    assert response.status_code == 401
    validate(instance=response.json(), schema=GENERIC_FAIL_SCHEMA)
    assert response.json()["status"] == "fail"
