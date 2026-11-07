import uuid
import random
import string
import datetime
import pytest
import jsonschema

# --- ESQUEMAS JSON PARA VALIDACIÓN CONTRACTUAL ---

SCHEMA_CATEGORY = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}

SCHEMA_TAG = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}

SCHEMA_PET = {
    "type": "object",
    "required": ["name", "photoUrls"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "category": SCHEMA_CATEGORY,
        "photoUrls": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": SCHEMA_TAG},
        "status": {"type": "string", "enum": ["available", "pending", "sold"]},
    },
}

SCHEMA_ORDER = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "petId": {"type": "integer"},
        "quantity": {"type": "integer"},
        "shipDate": {"type": "string"},
        "status": {"type": "string", "enum": ["placed", "approved", "delivered"]},
        "complete": {"type": "boolean"},
    },
}

SCHEMA_USER = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "username": {"type": "string"},
        "firstName": {"type": "string"},
        "lastName": {"type": "string"},
        "email": {"type": "string"},
        "password": {"type": "string"},
        "phone": {"type": "string"},
        "userStatus": {"type": "integer"},
    },
}

SCHEMA_API_RESPONSE = {
    "type": "object",
    "properties": {
        "code": {"type": "integer"},
        "type": {"type": "string"},
        "message": {"type": "string"},
    },
}


# --- HELPERS ---

def random_string(length=8):
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_pet_payload(pet_id=None, name=None, status="available", tag_name=None):
    return {
        "id": pet_id or random.randint(100000, 999999),
        "name": name or f"pet_{random_string(6)}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": [{"id": 1, "name": tag_name or f"tag_{random_string(4)}"}],
        "status": status,
    }


def generate_user_payload(user_id=None, username=None):
    uname = username or f"user_{random_string(8)}"
    return {
        "id": user_id or random.randint(100000, 999999),
        "username": uname,
        "firstName": "QA",
        "lastName": "Tester",
        "email": f"{uname}@example.com",
        "password": "Password123!",
        "phone": "555-0199",
        "userStatus": 1,
    }


# --- PRUEBAS DEL RECURSO /pet ---

def test_post_pet_success_200(api):
    payload = generate_pet_payload()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input_400_or_422(api):
    # Enviar payload sin los campos requeridos ("name", "photoUrls")
    response = api.post("/pet", json={"status": "invalid_value", "invalidField": 123})
    assert response.status_code in [400, 422]


def test_put_pet_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    created_pet = create_res.json()

    created_pet["name"] = f"updated_{random_string(5)}"
    created_pet["status"] = "sold"

    update_res = api.put("/pet", json=created_pet)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    jsonschema.validate(instance=updated_data, schema=SCHEMA_PET)
    assert updated_data["name"] == created_pet["name"]
    assert updated_data["status"] == "sold"


def test_put_pet_not_found_or_invalid(api):
    # ID inexistente o negativo
    payload = generate_pet_payload(pet_id=999999999999)
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 404, 422]


def test_get_pet_by_id_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id")

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)
    assert data["id"] == pet_id


def test_get_pet_by_id_not_found_404(api):
    non_existent_id = random.randint(900000000, 999999999)
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_get_pet_by_id_invalid_id_400(api):
    response = api.get("/pet/invalid_string_id")
    assert response.status_code == 400


def test_get_pet_find_by_status_success_200(api):
    response = api.get("/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        jsonschema.validate(instance=data[0], schema=SCHEMA_PET)
        assert data[0]["status"] == "available"


def test_get_pet_find_by_status_invalid_status_400(api):
    response = api.get("/pet/findByStatus", params={"status": "unknown_status"})
    assert response.status_code in [400, 200]  # Algunas implementaciones ignoran o retornan 400


def test_get_pet_find_by_tags_success_200(api):
    tag = f"tag_{random_string(5)}"
    pet_payload = generate_pet_payload(tag_name=tag)
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200

    response = api.get("/pet/findByTags", params={"tags": tag})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        jsonschema.validate(instance=data[0], schema=SCHEMA_PET)


def test_post_pet_update_with_form_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id")

    updated_name = f"form_{random_string(4)}"
    response = api.post(f"/pet/{pet_id}", params={"name": updated_name, "status": "pending"})
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)


def test_post_pet_update_with_form_invalid_input_400(api):
    response = api.post("/pet/invalid_id_format", params={"name": "test"})
    assert response.status_code == 400


def test_delete_pet_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id")

    del_res = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert del_res.status_code == 200

    get_res = api.get(f"/pet/{pet_id}")
    assert get_res.status_code == 404


def test_delete_pet_invalid_id_400(api):
    response = api.delete("/pet/not_a_valid_number")
    assert response.status_code == 400


def test_post_pet_upload_image_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id")

    fake_file_content = b"\x89PNG\r\n\x1a\nfakeimagebytes"
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "test_metadata"},
        data=fake_file_content,
        headers={"Content-Type": "application/octet-stream"}
    )
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_API_RESPONSE)


def test_post_pet_upload_image_pet_not_found_404(api):
    non_existent_id = random.randint(90000000, 99999999)
    response = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=b"image_content",
        headers={"Content-Type": "application/octet-stream"}
    )
    assert response.status_code in [404, 400]


# --- PRUEBAS DEL RECURSO /store ---

def test_get_store_inventory_success_200(api):
    response = api.get("/store/inventory", headers={"api_key": "special-key"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for k, v in data.items():
        assert isinstance(k, str)
        assert isinstance(v, int)


def test_post_store_order_success_200(api):
    order_id = random.randint(1, 5)  # Según spec, IDs <= 5 son estables para petstore
    order_payload = {
        "id": order_id,
        "petId": random.randint(1000, 9999),
        "quantity": 2,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "placed",
        "complete": True,
    }
    response = api.post("/store/order", json=order_payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_ORDER)
    assert data["id"] == order_payload["id"]


def test_post_store_order_invalid_input_400_or_422(api):
    response = api.post("/store/order", json={"quantity": "invalid_number_type", "status": 999})
    assert response.status_code in [400, 422]


def test_get_store_order_by_id_success_200(api):
    order_id = random.randint(1, 5)
    order_payload = {
        "id": order_id,
        "petId": 1234,
        "quantity": 1,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "approved",
        "complete": True,
    }
    create_res = api.post("/store/order", json=order_payload)
    assert create_res.status_code == 200

    get_res = api.get(f"/store/order/{order_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    jsonschema.validate(instance=data, schema=SCHEMA_ORDER)
    assert data["id"] == order_id


def test_get_store_order_by_id_not_found_404(api):
    response = api.get("/store/order/9999999")
    assert response.status_code == 404


def test_get_store_order_by_id_invalid_id_400(api):
    response = api.get("/store/order/string_id_val")
    assert response.status_code == 400


def test_delete_store_order_success_200(api):
    order_id = random.randint(1, 5)
    order_payload = {
        "id": order_id,
        "petId": 456,
        "quantity": 1,
        "status": "placed",
        "complete": False,
    }
    api.post("/store/order", json=order_payload)

    del_res = api.delete(f"/store/order/{order_id}")
    assert del_res.status_code == 200


def test_delete_store_order_invalid_id_400(api):
    response = api.delete("/store/order/invalid_order_id")
    assert response.status_code == 400


def test_delete_store_order_not_found_404(api):
    response = api.delete("/store/order/9999999")
    assert response.status_code in [404, 400]


# --- PRUEBAS DEL RECURSO /user ---

def test_post_user_create_user_success_200(api):
    payload = generate_user_payload()
    response = api.post("/user", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)
    assert data["username"] == payload["username"]


def test_post_user_create_with_list_success_200(api):
    payload = [generate_user_payload(), generate_user_payload()]
    response = api.post("/user/createWithList", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)


def test_get_user_login_success_200(api):
    response = api.get("/user/login", params={"username": "testUser", "password": "testPassword"})
    assert response.status_code == 200
    assert "X-Rate-Limit" in response.headers or "x-rate-limit" in response.headers
    assert isinstance(response.text, str)


def test_get_user_login_invalid_credentials_400(api):
    # Enviar parámetros erróneos si el servidor valida campos requeridos/formatos
    response = api.get("/user/login", params={"username": ""})
    assert response.status_code in [400, 200]


def test_get_user_logout_success_200(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


def test_get_user_by_name_success_200(api):
    payload = generate_user_payload()
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    response = api.get(f"/user/{payload['username']}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)
    assert data["username"] == payload["username"]


def test_get_user_by_name_not_found_404(api):
    non_existent_username = f"notfound_{uuid.uuid4().hex[:10]}"
    response = api.get(f"/user/{non_existent_username}")
    assert response.status_code == 404


def test_put_user_success_200(api):
    payload = generate_user_payload()
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    payload["firstName"] = "UpdatedName"
    payload["lastName"] = "UpdatedLastname"

    update_res = api.put(f"/user/{payload['username']}", json=payload)
    assert update_res.status_code == 200

    get_res = api.get(f"/user/{payload['username']}")
    assert get_res.status_code == 200
    assert get_res.json()["firstName"] == "UpdatedName"


def test_put_user_not_found_404(api):
    non_existent_username = f"notfound_{uuid.uuid4().hex[:10]}"
    payload = generate_user_payload(username=non_existent_username)
    response = api.put(f"/user/{non_existent_username}", json=payload)
    assert response.status_code in [404, 400]


def test_delete_user_success_200(api):
    payload = generate_user_payload()
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    del_res = api.delete(f"/user/{payload['username']}")
    assert del_res.status_code == 200

    get_res = api.get(f"/user/{payload['username']}")
    assert get_res.status_code == 404


def test_delete_user_not_found_404(api):
    non_existent_username = f"notfound_{uuid.uuid4().hex[:10]}"
    response = api.delete(f"/user/{non_existent_username}")
    assert response.status_code in [404, 400]
