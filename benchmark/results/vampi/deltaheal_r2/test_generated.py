import uuid
import requests
import jsonschema


def generate_unique_string(prefix="test_"):
    return f"{prefix}{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Tests for DELETE /users/v1/{username}
# ---------------------------------------------------------------------------


def test_delete_user_success(api):
    # Se crea primero un usuario para asegurar la existencia y mantener idempotencia
    username = generate_unique_string("user_del_")
    email = f"{username}@example.com"
    password = "Password123!"

    register_payload = {
        "username": username,
        "password": password,
        "email": email,
    }
    # Registro de usuario (endpoint estándar de VAmPI para crear usuario)
    reg_res = api.post("/users/v1/register", json=register_payload)
    # Si el registro no está disponible o falla, intentamos la eliminación directa si el usuario fue creado
    assert reg_res.status_code in [200, 201], f"Fallo al crear usuario previo: {reg_res.text}"

    # Eliminación con usuario admin provisto en la fixture api
    response = api.delete(f"/users/v1/{username}")
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


def test_delete_user_not_found(api):
    non_existent_user = generate_unique_string("non_existent_")
    response = api.delete(f"/users/v1/{non_existent_user}")
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


def test_delete_user_unauthorized(base_url):
    username = generate_unique_string("user_unauth_")
    # Petición sin token de autenticación
    response = requests.delete(f"{base_url}/users/v1/{username}")
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


def test_put_password_success(api):
    # Se crea un usuario nuevo para modificar su contraseña
    username = generate_unique_string("user_pwd_")
    email = f"{username}@example.com"
    reg_payload = {
        "username": username,
        "password": "initialPassword1!",
        "email": email,
    }
    reg_res = api.post("/users/v1/register", json=reg_payload)
    assert reg_res.status_code in [200, 201]

    payload = {"password": "newSecurePassword2@"}
    response = api.put(f"/users/v1/{username}/password", json=payload)
    assert response.status_code == 204
    assert response.text == "" or response.text is None


def test_put_password_invalid_request(api):
    username = generate_unique_string("user_bad_req_")
    # Enviar cuerpo malformado o vacío sin el campo esperado 'password'
    payload = {"invalid_field": "some_value"}
    response = api.put(f"/users/v1/{username}/password", json=payload)
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


def test_put_password_unauthorized(base_url):
    payload = {"password": "passUnauthorized"}
    response = requests.put(f"{base_url}/users/v1/name1/password", json=payload)
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


def test_post_book_success(api):
    book_title = generate_unique_string("bookTitle")
    payload = {
        "book_title": book_title,
        "secret": "top_secret_content_123",
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


def test_post_book_already_exists(api):
    book_title = generate_unique_string("bookTitleDup")
    payload = {
        "book_title": book_title,
        "secret": "original_secret",
    }
    # Primera creación
    res1 = api.post("/books/v1", json=payload)
    assert res1.status_code == 200

    # Intento de duplicado
    res2 = api.post("/books/v1", json=payload)
    assert res2.status_code == 400

    schema = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["fail"]},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
    }
    data = res2.json()
    jsonschema.validate(instance=data, schema=schema)
    assert data["status"] == "fail"


def test_post_book_unauthorized(base_url):
    payload = {
        "book_title": generate_unique_string("unauthBook"),
        "secret": "secret_data",
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


def test_get_book_by_title_success(api):
    book_title = generate_unique_string("bookTitleGet")
    secret_value = "my_classified_secret"
    post_payload = {
        "book_title": book_title,
        "secret": secret_value,
    }
    # El usuario actual (admin) crea el libro para ser el propietario
    create_res = api.post("/books/v1", json=post_payload)
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
    data = response.json()
    jsonschema.validate(instance=data, schema=schema)
    assert len(data) > 0
    assert data[0]["book_title"] == book_title
    assert data[0]["secret"] == secret_value


def test_get_book_by_title_not_found(api):
    non_existent_book = generate_unique_string("missingBook_")
    response = api.get(f"/books/v1/{non_existent_book}")
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


def test_get_book_by_title_unauthorized(base_url):
    response = requests.get(f"{base_url}/books/v1/anyBookTitle")
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
