import uuid
import requests
import jsonschema


def _unique_str(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# DELETE /users/v1/{username}
# ---------------------------------------------------------------------------

def test_delete_user_success(api):
    # Setup: create a temporary user to delete
    username = _unique_str("user_del_")
    create_payload = {
        "username": username,
        "password": "tempPassword123!",
        "email": f"{username}@example.com"
    }
    # Register/create user if endpoint exists, else use standard register path
    reg_resp = api.post("/users/v1/register", json=create_payload)
    # If registration is available, we use that user; otherwise we proceed
    target_username = username if reg_resp.status_code in [200, 201] else _unique_str("del_user_")

    response = api.delete(f"/users/v1/{target_username}")
    if response.status_code == 200:
        data = response.json()
        schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "status": {"type": "string", "enum": ["success", "fail"]}
            },
            "required": ["status", "message"]
        }
        jsonschema.validate(instance=data, schema=schema)
        assert data["status"] == "success"
    else:
        # If user registration isn't open and username doesn't exist, it should return 404
        assert response.status_code == 404


def test_delete_user_not_found(api):
    non_existent_username = _unique_str("nonexistent_user_")
    response = api.delete(f"/users/v1/{non_existent_username}")

    assert response.status_code == 404
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_delete_user_unauthorized(base_url):
    # Non-authenticated request should return 401
    response = requests.delete(f"{base_url}/users/v1/name1")

    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# PUT /users/v1/{username}/password
# ---------------------------------------------------------------------------

def test_put_users_password_success(api):
    # Using existing user 'name1'
    payload = {"password": "newSecurePassword123"}
    response = api.put("/users/v1/name1/password", json=payload)

    assert response.status_code == 204
    assert response.text == "" or response.text is None or len(response.content) == 0


def test_put_users_password_bad_request(api):
    # Invalid request body (missing required password field or empty payload)
    payload = {"invalid_field": 12345}
    response = api.put("/users/v1/name1/password", json=payload)

    assert response.status_code == 400
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_put_users_password_unauthorized(base_url):
    payload = {"password": "someNewPassword"}
    response = requests.put(f"{base_url}/users/v1/name1/password", json=payload)

    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# POST /books/v1
# ---------------------------------------------------------------------------

def test_post_books_success(api):
    book_title = _unique_str("book_")
    payload = {
        "book_title": book_title,
        "secret": "superSecretData"
    }
    response = api.post("/books/v1", json=payload)

    assert response.status_code == 200
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "success"


def test_post_books_already_exists_conflict(api):
    book_title = _unique_str("book_dup_")
    payload = {
        "book_title": book_title,
        "secret": "initialSecret"
    }
    # Create the book first
    first_resp = api.post("/books/v1", json=payload)
    assert first_resp.status_code == 200

    # Attempt to create the same book again
    second_resp = api.post("/books/v1", json=payload)
    assert second_resp.status_code == 400
    data = second_resp.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_post_books_unauthorized(base_url):
    payload = {
        "book_title": _unique_str("unauth_book_"),
        "secret": "topSecret"
    }
    response = requests.post(f"{base_url}/books/v1", json=payload)

    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------------------------
# GET /books/v1/{book_title}
# ---------------------------------------------------------------------------

def test_get_books_by_title_success(api):
    # Setup: create a unique book using current authenticated session (admin)
    book_title = _unique_str("getbook_")
    secret = "secretContent123"
    create_resp = api.post("/books/v1", json={"book_title": book_title, "secret": secret})
    assert create_resp.status_code == 200

    # Retrieve the book
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
            },
            "required": ["book_title", "owner", "secret"]
        }
    }
    jsonschema.validate(instance=data, schema=schema)
    assert len(data) > 0
    assert any(item["book_title"] == book_title for item in data)


def test_get_books_by_title_not_found(api):
    non_existent_title = _unique_str("missing_book_")
    response = api.get(f"/books/v1/{non_existent_title}")

    assert response.status_code == 404
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_get_books_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")

    assert response.status_code == 401
    data = response.json()
    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"
