import uuid
import random
import jsonschema
import pytest

# --- JSON SCHEMAS FROM OPENAPI SPEC ---

CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}

TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
    },
}

PET_SCHEMA = {
    "type": "object",
    "required": ["name", "photoUrls"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "category": CATEGORY_SCHEMA,
        "photoUrls": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": TAG_SCHEMA},
        "status": {"type": "string", "enum": ["available", "pending", "sold"]},
    },
}

ORDER_SCHEMA = {
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

USER_SCHEMA = {
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

API_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "integer"},
        "type": {"type": "string"},
        "message": {"type": "string"},
    },
}


# --- HELPER FUNCTIONS ---

def generate_unique_id():
    return random.randint(100000, 999999)


def make_pet_payload(pet_id=None, name="test_doggie", status="available", tags=None):
    if pet_id is None:
        pet_id = generate_unique_id()
    if tags is None:
        tags = [{"id": 1, "name": f"tag_{uuid.uuid4().hex[:6]}"}]
    return {
        "id": pet_id,
        "name": name,
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo.jpg"],
        "tags": tags,
        "status": status,
    }


def make_order_payload(order_id=None, pet_id=None, status="placed"):
    if order_id is None:
        order_id = random.randint(1, 5)
    if pet_id is None:
        pet_id = generate_unique_id()
    return {
        "id": order_id,
        "petId": pet_id,
        "quantity": 1,
        "shipDate": "2026-01-01T00:00:00.000Z",
        "status": status,
        "complete": True,
    }


def make_user_payload(username=None):
    if username is None:
        username = f"user_{uuid.uuid4().hex[:8]}"
    return {
        "id": generate_unique_id(),
        "username": username,
        "firstName": "QA",
        "lastName": "Tester",
        "email": f"{username}@example.com",
        "password": "SecretPassword123!",
        "phone": "555-0199",
        "userStatus": 1,
    }


# ==============================================================================
# PET ENDPOINTS
# ==============================================================================

def test_post_pet_success(api):
    payload = make_pet_payload()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input(api):
    # Required fields missing according to schema: 'name' and 'photoUrls'
    response = api.post("/pet", json={"status": "invalid_status_value"})
    assert response.status_code in (400, 422)


def test_put_pet_success(api):
    payload = make_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200

    created_id = create_res.json().get("id", payload["id"])
    updated_payload = make_pet_payload(pet_id=created_id, name="updated_doggie", status="sold")

    update_res = api.put("/pet", json=updated_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    jsonschema.validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == "updated_doggie"
    assert data["status"] == "sold"


def test_put_pet_invalid_id(api):
    # Non-integer id inside JSON payload to trigger validation/bad-request error
    invalid_payload = {
        "id": "not-a-valid-int64-id",
        "name": "doggie",
        "photoUrls": ["https://example.com/p.jpg"],
    }
    response = api.put("/pet", json=invalid_payload)
    assert response.status_code in (400, 422)


def test_put_pet_not_found(api):
    non_existent_payload = make_pet_payload(pet_id=9999999999999)
    response = api.put("/pet", json=non_existent_payload)
    assert response.status_code in (200, 404)


def test_get_find_pets_by_status_success(api):
    for status in ["available", "pending", "sold"]:
        response = api.get("/pet/findByStatus", params={"status": status})
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for pet in data:
            jsonschema.validate(instance=pet, schema=PET_SCHEMA)


def test_get_find_pets_by_status_invalid(api):
    response = api.get("/pet/findByStatus", params={"status": "unknown_status_xyz"})
    assert response.status_code in (400, 200)


def test_get_find_pets_by_tags_success(api):
    tag_name = f"tag_{uuid.uuid4().hex[:6]}"
    payload = make_pet_payload(tags=[{"id": 1, "name": tag_name}])
    api.post("/pet", json=payload)

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        jsonschema.validate(instance=pet, schema=PET_SCHEMA)


def test_get_find_pets_by_tags_empty(api):
    response = api.get("/pet/findByTags", params={"tags": ""})
    assert response.status_code in (200, 400)


def test_get_pet_by_id_success(api):
    payload = make_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_not_found(api):
    non_existent_id = 999999999998
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_get_pet_by_id_invalid(api):
    response = api.get("/pet/invalid_id_string")
    assert response.status_code in (400, 404)


def test_post_update_pet_with_form_success(api):
    payload = make_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    updated_name = "form_updated_pet"
    updated_status = "sold"
    response = api.post(f"/pet/{pet_id}", params={"name": updated_name, "status": updated_status})
    assert response.status_code == 200

    verify_res = api.get(f"/pet/{pet_id}")
    if verify_res.status_code == 200:
        data = verify_res.json()
        assert data["name"] == updated_name
        assert data["status"] == updated_status


def test_post_update_pet_with_form_invalid_input(api):
    response = api.post("/pet/not_a_valid_id", params={"name": "test", "status": "sold"})
    assert response.status_code in (400, 404)


def test_delete_pet_success(api):
    payload = make_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    delete_res = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert delete_res.status_code in (200, 204)

    get_res = api.get(f"/pet/{pet_id}")
    assert get_res.status_code == 404


def test_delete_pet_invalid_id(api):
    response = api.delete("/pet/invalid_pet_id_string")
    assert response.status_code in (400, 404)


def test_post_upload_image_success(api):
    payload = make_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_binary_stream"
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "profile_picture"},
        data=binary_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=API_RESPONSE_SCHEMA)


def test_post_upload_image_not_found(api):
    non_existent_id = 999999999997
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=b"random_bytes",
        headers=headers,
    )
    assert response.status_code in (404, 400)


# ==============================================================================
# STORE ENDPOINTS
# ==============================================================================

def test_get_store_inventory_success(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for key, value in data.items():
        assert isinstance(key, str)
        assert isinstance(value, int)


def test_post_store_order_success(api):
    payload = make_order_payload(order_id=generate_unique_id())
    response = api.post("/store/order", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=ORDER_SCHEMA)
    assert data["petId"] == payload["petId"]
    assert data["status"] == payload["status"]


def test_post_store_order_invalid_input(api):
    invalid_payload = {"quantity": "invalid_integer_string"}
    response = api.post("/store/order", json=invalid_payload)
    assert response.status_code in (400, 422)


def test_get_store_order_by_id_success(api):
    order_id = random.randint(1, 5)
    payload = make_order_payload(order_id=order_id)
    create_res = api.post("/store/order", json=payload)
    assert create_res.status_code == 200

    response = api.get(f"/store/order/{order_id}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_get_store_order_by_id_not_found(api):
    # Contract notes: IDs > 10 or <= 5 are valid, other values or non-existent generate exceptions/404
    non_existent_id = 99999999
    response = api.get(f"/store/order/{non_existent_id}")
    assert response.status_code == 404


def test_get_store_order_by_id_invalid(api):
    response = api.get("/store/order/non_integer_id")
    assert response.status_code in (400, 404)


def test_delete_store_order_success(api):
    # Spec states: For valid response try integer IDs with value < 1000
    order_id = random.randint(1, 500)
    payload = make_order_payload(order_id=order_id)
    create_res = api.post("/store/order", json=payload)
    assert create_res.status_code == 200

    delete_res = api.delete(f"/store/order/{order_id}")
    assert delete_res.status_code == 200

    get_res = api.get(f"/store/order/{order_id}")
    assert get_res.status_code == 404


def test_delete_store_order_not_found(api):
    non_existent_order_id = 999
    response = api.delete(f"/store/order/{non_existent_order_id}")
    assert response.status_code in (404, 200)


def test_delete_store_order_invalid_id(api):
    response = api.delete("/store/order/invalid_order_id")
    assert response.status_code in (400, 404)


# ==============================================================================
# USER ENDPOINTS
# ==============================================================================

def test_post_create_user_success(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    payload = make_user_payload(username=username)
    response = api.post("/user", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_post_create_users_with_list_success(api):
    users = [
        make_user_payload(f"user_batch1_{uuid.uuid4().hex[:6]}"),
        make_user_payload(f"user_batch2_{uuid.uuid4().hex[:6]}"),
    ]
    response = api.post("/user/createWithList", json=users)
    assert response.status_code == 200
    data = response.json()
    if isinstance(data, list):
        for user_data in data:
            jsonschema.validate(instance=user_data, schema=USER_SCHEMA)
    elif isinstance(data, dict):
        jsonschema.validate(instance=data, schema=USER_SCHEMA)


def test_get_user_login_success(api):
    response = api.get(
        "/user/login",
        params={"username": "theUser", "password": "password123"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200
    assert "X-Rate-Limit" in response.headers or "x-rate-limit" in response.headers
    assert "X-Expires-After" in response.headers or "x-expires-after" in response.headers

    # El schema documenta un tipo string; la respuesta puede venir como texto plano o JSON serializado
    content_type = response.headers.get("Content-Type", "")
    if "application/json" in content_type:
        try:
            data = response.json()
        except Exception:
            data = response.text
    else:
        data = response.text

    assert isinstance(data, str)
    assert len(data) > 0


def test_get_user_login_invalid(api):
    # Testing error case documented for bad username/password format or missing parameters
    response = api.get("/user/login", params={})
    assert response.status_code in (200, 400)


def test_get_user_logout_success(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


def test_get_user_by_name_success(api):
    username = f"user_fetch_{uuid.uuid4().hex[:8]}"
    payload = make_user_payload(username=username)
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    response = api.get(f"/user/{username}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_get_user_by_name_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    response = api.get(f"/user/{non_existent_username}")
    assert response.status_code == 404


def test_put_update_user_success(api):
    username = f"user_update_{uuid.uuid4().hex[:8]}"
    payload = make_user_payload(username=username)
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    updated_payload = payload.copy()
    updated_payload["firstName"] = "UpdatedFirst"
    updated_payload["lastName"] = "UpdatedLast"

    update_res = api.put(f"/user/{username}", json=updated_payload)
    assert update_res.status_code == 200

    get_res = api.get(f"/user/{username}")
    if get_res.status_code == 200:
        data = get_res.json()
        assert data["firstName"] == "UpdatedFirst"
        assert data["lastName"] == "UpdatedLast"


def test_put_update_user_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    payload = make_user_payload(username=non_existent_username)
    response = api.put(f"/user/{non_existent_username}", json=payload)
    assert response.status_code in (404, 200)


def test_delete_user_success(api):
    username = f"user_del_{uuid.uuid4().hex[:8]}"
    payload = make_user_payload(username=username)
    create_res = api.post("/user", json=payload)
    assert create_res.status_code == 200

    delete_res = api.delete(f"/user/{username}")
    assert delete_res.status_code == 200

    get_res = api.get(f"/user/{username}")
    assert get_res.status_code == 404


def test_delete_user_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    response = api.delete(f"/user/{non_existent_username}")
    assert response.status_code in (404, 400)
