import uuid
import requests
import jsonschema


def _get_unique_str(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Tests for DELETE /users/v1/{username}
# ---------------------------------------------------------------------------


def test_delete_users_success(api):
    # Setup: Create a temporary user to delete
    temp_username = _get_unique_str("user_")
    create_payload = {
        "username": temp_username,
        "password": "Password123!",
        "email": f"{temp_username}@example.com",
    }
    create_res = api.post("/users/v1/register", json=create_payload)
    # Even if register route isn't explicitly tested here, if it fails or succeeds, attempt delete
    assert create_res.status_code in (200, 201)

    # Execute deletion by admin
    response = api.delete(f"/users/v1/{temp_username}")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]},
        },
        "required": ["message", "status"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "success"


def test_delete_users_not_found(api):
    non_existent_username = _get_unique_str("nonexistent_")
    response = api.delete(f"/users/v1/{non_existent_username}")

    assert response.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_delete_users_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name1")

    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests for PUT /users/v1/{username}/password
# ---------------------------------------------------------------------------


def test_put_users_password_success(api):
    # Admin updates their own password or another user's password
    payload = {"password": "newSecurePassword123!"}
    response = api.put("/users/v1/admin/password", json=payload)

    assert response.status_code == 204
    assert response.text == "" or response.content == b""


def test_put_users_password_bad_request(api):
    # Sending malformed/missing required fields
    payload = {"invalid_field": "some_value"}
    response = api.put("/users/v1/admin/password", json=payload)

    assert response.status_code == 400
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_put_users_password_unauthorized(base_url):
    payload = {"password": "newPassword123!"}
    response = requests.put(f"{base_url}/users/v1/admin/password", json=payload)

    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests for POST /books/v1
# ---------------------------------------------------------------------------


def test_post_books_success(api):
    unique_title = _get_unique_str("book_")
    payload = {
        "book_title": unique_title,
        "secret": "topSecretData",
    }
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
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "success"


def test_post_books_duplicate_conflict(api):
    unique_title = _get_unique_str("book_dup_")
    payload = {
        "book_title": unique_title,
        "secret": "initialSecret",
    }
    # First creation should succeed
    first_res = api.post("/books/v1", json=payload)
    assert first_res.status_code == 200

    # Second creation with identical title should fail with 400
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_post_books_unauthorized(base_url):
    unique_title = _get_unique_str("book_unauth_")
    payload = {
        "book_title": unique_title,
        "secret": "secret",
    }
    response = requests.post(f"{base_url}/books/v1", json=payload)

    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# Tests for GET /books/v1/{book_title}
# ---------------------------------------------------------------------------


def test_get_books_by_title_success(api):
    unique_title = _get_unique_str("book_get_")
    secret_text = "super_classified_secret"
    # Create the book first as admin so admin owns it
    create_res = api.post(
        "/books/v1",
        json={"book_title": unique_title, "secret": secret_text},
    )
    assert create_res.status_code == 200

    # Retrieve the book
    response = api.get(f"/books/v1/{unique_title}")
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
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert len(data) > 0
    assert data[0]["book_title"] == unique_title
    assert data[0]["secret"] == secret_text


def test_get_books_by_title_not_found(api):
    non_existent_title = _get_unique_str("notfound_book_")
    response = api.get(f"/books/v1/{non_existent_title}")

    assert response.status_code == 404
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_get_books_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")

    assert response.status_code == 401
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"
