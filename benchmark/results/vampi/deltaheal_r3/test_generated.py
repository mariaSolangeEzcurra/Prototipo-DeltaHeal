import uuid
import requests
import jsonschema


def generate_unique_name(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------
# Tests for DELETE /users/v1/{username}
# ---------------------------------------------------------

def test_delete_user_success(api):
    # Setup: Create a new user first using an endpoint (or registration) if available,
    # or test deletion on a created user. Since user creation is not in spec, we use
    # a unique user or test user handling. Let's create one via standard endpoint or
    # test existing name2 (if independent setup permits) or try deleting a disposable user.
    # Note: To ensure independence and keep existing name1/name2/admin intact,
    # we create a user if /users/v1/register exists, otherwise we delete an isolated disposable user.
    username = generate_unique_name("user")
    # Attempt to register user so test is self-contained
    reg_payload = {"username": username, "password": "Password123!", "email": f"{username}@test.com"}
    reg_res = api.post("/users/v1/register", json=reg_payload)
    target_user = username if reg_res.status_code in (200, 201) else "name2"

    response = api.delete(f"/users/v1/{target_user}")
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        },
        "required": ["message", "status"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "success"


def test_delete_user_not_found(api):
    non_existent_user = generate_unique_name("nonexistent")
    response = api.delete(f"/users/v1/{non_existent_user}")
    assert response.status_code == 404

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_delete_user_unauthorized(base_url):
    response = requests.delete(f"{base_url}/users/v1/name1")
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------
# Tests for PUT /users/v1/{username}/password
# ---------------------------------------------------------

def test_put_password_success(api):
    payload = {"password": "newSecurePassword123"}
    # The authenticated user is admin
    response = api.put("/users/v1/admin/password", json=payload)
    assert response.status_code == 204
    assert response.text == "" or response.content == b""


def test_put_password_bad_request_malformed_data(api):
    # Sending invalid payload without 'password' field
    payload = {"invalid_field": "some_value"}
    response = api.put("/users/v1/admin/password", json=payload)
    assert response.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_put_password_unauthorized(base_url):
    payload = {"password": "unauthorizedPassword123"}
    response = requests.put(f"{base_url}/users/v1/admin/password", json=payload)
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------
# Tests for POST /books/v1
# ---------------------------------------------------------

def test_post_books_success(api):
    unique_title = generate_unique_name("bookTitle")
    payload = {
        "book_title": unique_title,
        "secret": "topSecretInfo123"
    }
    response = api.post("/books/v1", json=payload)
    assert response.status_code == 200

    schema = {
        "type": "object",
        "properties": {
            "message": {"type": "string"},
            "status": {"type": "string", "enum": ["success", "fail"]}
        },
        "required": ["message", "status"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "success"


def test_post_books_already_exists(api):
    unique_title = generate_unique_name("bookTitle")
    payload = {
        "book_title": unique_title,
        "secret": "originalSecret"
    }
    # Create the book first
    first_resp = api.post("/books/v1", json=payload)
    assert first_resp.status_code == 200

    # Try creating the book with the same title again
    duplicate_resp = api.post("/books/v1", json=payload)
    assert duplicate_resp.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = duplicate_resp.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_post_books_unauthorized(base_url):
    unique_title = generate_unique_name("bookTitle")
    payload = {
        "book_title": unique_title,
        "secret": "unauthSecret"
    }
    response = requests.post(f"{base_url}/books/v1", json=payload)
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


# ---------------------------------------------------------
# Tests for GET /books/v1/{book_title}
# ---------------------------------------------------------

def test_get_book_by_title_success(api):
    unique_title = generate_unique_name("bookTitle")
    secret_value = "super_classified_content"
    # Create the book so the authenticated user (admin) is the owner
    create_resp = api.post("/books/v1", json={"book_title": unique_title, "secret": secret_value})
    assert create_resp.status_code == 200

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
                "secret": {"type": "string"}
            },
            "required": ["book_title", "owner", "secret"]
        }
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert len(data) > 0
    assert data[0]["book_title"] == unique_title
    assert data[0]["secret"] == secret_value


def test_get_book_by_title_not_found(api):
    non_existent_title = generate_unique_name("nonExistentBook")
    response = api.get(f"/books/v1/{non_existent_title}")
    assert response.status_code == 404

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_get_book_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/bookTitle1")
    assert response.status_code == 401

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"}
        },
        "required": ["status", "message"]
    }
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"
