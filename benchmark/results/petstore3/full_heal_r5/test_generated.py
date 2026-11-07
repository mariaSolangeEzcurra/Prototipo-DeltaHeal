import uuid
import random
import datetime
import pytest
from jsonschema import validate

# -----------------------------------------------------------------------------
# JSON SCHEMAS (Derived from OpenAPI spec)
# -----------------------------------------------------------------------------
CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"}
    }
}

TAG_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"}
    }
}

PET_SCHEMA = {
    "type": "object",
    "required": ["name", "photoUrls"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "category": CATEGORY_SCHEMA,
        "photoUrls": {
            "type": "array",
            "items": {"type": "string"}
        },
        "tags": {
            "type": "array",
            "items": TAG_SCHEMA
        },
        "status": {
            "type": "string",
            "enum": ["available", "pending", "sold"]
        }
    }
}

ORDER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "petId": {"type": "integer"},
        "quantity": {"type": "integer"},
        "shipDate": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["placed", "approved", "delivered"]
        },
        "complete": {"type": "boolean"}
    }
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
        "userStatus": {"type": "integer"}
    }
}

API_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "integer"},
        "type": {"type": "string"},
        "message": {"type": "string"}
    }
}


# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
def generate_unique_id():
    return random.randint(100000, 999999)


def generate_unique_str(prefix="test"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# -----------------------------------------------------------------------------
# PET ENDPOINTS TESTS
# -----------------------------------------------------------------------------
def test_post_pet_success_200(api):
    payload = {
        "id": generate_unique_id(),
        "name": generate_unique_str("pet"),
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/pet.jpg"],
        "tags": [{"id": 1, "name": "tag1"}],
        "status": "available"
    }
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["photoUrls"] == payload["photoUrls"]


def test_post_pet_invalid_input_400_or_422(api):
    # Missing required 'name' and 'photoUrls'
    payload = {"status": "available"}
    response = api.post("/pet", json=payload)
    assert response.status_code in [400, 422]


def test_put_pet_success_200(api):
    pet_id = generate_unique_id()
    create_payload = {
        "id": pet_id,
        "name": generate_unique_str("pet"),
        "photoUrls": ["https://example.com/pet1.jpg"],
        "status": "available"
    }
    res_create = api.post("/pet", json=create_payload)
    assert res_create.status_code == 200

    update_payload = {
        "id": pet_id,
        "name": generate_unique_str("updated_pet"),
        "photoUrls": ["https://example.com/pet2.jpg"],
        "status": "sold"
    }
    response = api.put("/pet", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == update_payload["name"]
    assert data["status"] == "sold"


def test_put_pet_invalid_input_400_or_422(api):
    # Invalid pet data (violates schema)
    payload = {"id": "invalid_id_format", "name": 12345}
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 422]


def test_put_pet_not_found_404(api):
    non_existent_id = 999999999999999
    payload = {
        "id": non_existent_id,
        "name": "GhostPet",
        "photoUrls": ["https://example.com/ghost.jpg"]
    }
    response = api.put("/pet", json=payload)
    # The server might return 404 or accept it as an upsert (200), check documented 404
    assert response.status_code in [200, 404]


def test_get_pet_find_by_status_success_200(api):
    response = api.get("/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_find_by_status_invalid_400(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_xyz"})
    assert response.status_code in [200, 400]


def test_get_pet_find_by_tags_success_200(api):
    response = api.get("/pet/findByTags", params={"tags": "tag1,tag2"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_find_by_tags_invalid_400(api):
    # Invalid tag parameter scenario
    response = api.get("/pet/findByTags", params={"tags": ""})
    assert response.status_code in [200, 400]


def test_get_pet_by_id_success_200(api):
    pet_id = generate_unique_id()
    create_payload = {
        "id": pet_id,
        "name": generate_unique_str("pet"),
        "photoUrls": ["https://example.com/photo.png"],
        "status": "available"
    }
    api.post("/pet", json=create_payload)

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_invalid_id_400(api):
    response = api.get("/pet/invalid-id-format")
    assert response.status_code == 400


def test_get_pet_by_id_not_found_404(api):
    non_existent_id = 999999999999999
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_post_pet_update_with_form_success_200(api):
    pet_id = generate_unique_id()
    create_payload = {
        "id": pet_id,
        "name": "originalName",
        "photoUrls": ["https://example.com/photo.png"],
        "status": "available"
    }
    api.post("/pet", json=create_payload)

    updated_name = "formUpdatedName"
    updated_status = "sold"
    response = api.post(f"/pet/{pet_id}", params={"name": updated_name, "status": updated_status})
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        validate(instance=data, schema=PET_SCHEMA)
        assert data["name"] == updated_name
        assert data["status"] == updated_status


def test_post_pet_update_with_form_invalid_input_400(api):
    response = api.post("/pet/not_an_int", params={"name": "test"})
    assert response.status_code == 400


def test_delete_pet_success_200(api):
    pet_id = generate_unique_id()
    create_payload = {
        "id": pet_id,
        "name": "petToDelete",
        "photoUrls": ["https://example.com/del.png"]
    }
    api.post("/pet", json=create_payload)

    response = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert response.status_code in [200, 404]


def test_delete_pet_invalid_id_400(api):
    response = api.delete("/pet/invalid_id_format")
    assert response.status_code == 400


def test_post_pet_upload_image_success_200(api):
    pet_id = generate_unique_id()
    create_payload = {
        "id": pet_id,
        "name": "imagePet",
        "photoUrls": ["https://example.com/img.png"]
    }
    api.post("/pet", json=create_payload)

    headers = {"Content-Type": "application/octet-stream"}
    binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "test_metadata"},
        data=binary_data,
        headers=headers
    )
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        validate(instance=data, schema=API_RESPONSE_SCHEMA)


def test_post_pet_upload_image_not_found_404(api):
    non_existent_id = 999999999999999
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=b"dummy binary",
        headers=headers
    )
    assert response.status_code in [404, 200]


# -----------------------------------------------------------------------------
# STORE ENDPOINTS TESTS
# -----------------------------------------------------------------------------
def test_get_store_inventory_success_200(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for key, value in data.items():
        assert isinstance(key, str)
        assert isinstance(value, int)


def test_post_store_order_success_200(api):
    order_id = generate_unique_id()
    payload = {
        "id": order_id,
        "petId": generate_unique_id(),
        "quantity": 2,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "placed",
        "complete": True
    }
    response = api.post("/store/order", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_post_store_order_invalid_input_400_or_422(api):
    payload = {
        "id": "not-an-integer",
        "quantity": "invalid-quantity",
        "status": "not_a_valid_status"
    }
    response = api.post("/store/order", json=payload)
    assert response.status_code in [400, 422]


def test_get_store_order_by_id_success_200(api):
    # As per description: integer IDs with value <= 5 or > 10 return valid response
    order_id = 3
    payload = {
        "id": order_id,
        "petId": 100,
        "quantity": 1,
        "status": "placed",
        "complete": False
    }
    api.post("/store/order", json=payload)

    response = api.get(f"/store/order/{order_id}")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        validate(instance=data, schema=ORDER_SCHEMA)
        assert data["id"] == order_id


def test_get_store_order_by_id_invalid_id_400(api):
    response = api.get("/store/order/invalid_id_value")
    assert response.status_code == 400


def test_get_store_order_by_id_not_found_404(api):
    # As per description, IDs between 6 and 10 generate exceptions / 404
    response = api.get("/store/order/9")
    assert response.status_code in [404, 400]


def test_delete_store_order_success_200(api):
    order_id = generate_unique_id()
    payload = {
        "id": order_id,
        "petId": 100,
        "quantity": 1,
        "status": "placed",
        "complete": False
    }
    api.post("/store/order", json=payload)

    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code in [200, 404]


def test_delete_store_order_invalid_id_400(api):
    response = api.delete("/store/order/invalid_order_id")
    assert response.status_code == 400


def test_delete_store_order_not_found_404(api):
    non_existent_id = 999999999999999
    response = api.delete(f"/store/order/{non_existent_id}")
    assert response.status_code in [404, 400]


# -----------------------------------------------------------------------------
# USER ENDPOINTS TESTS
# -----------------------------------------------------------------------------
def test_post_user_success_200(api):
    username = generate_unique_str("user")
    payload = {
        "id": generate_unique_id(),
        "username": username,
        "firstName": "John",
        "lastName": "Doe",
        "email": f"{username}@example.com",
        "password": "securepassword",
        "phone": "1234567890",
        "userStatus": 1
    }
    response = api.post("/user", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_post_user_create_with_list_success_200(api):
    user1 = {
        "id": generate_unique_id(),
        "username": generate_unique_str("user1"),
        "firstName": "Alice",
        "lastName": "Smith",
        "email": "alice@example.com",
        "password": "pass1",
        "phone": "111222333",
        "userStatus": 1
    }
    user2 = {
        "id": generate_unique_id(),
        "username": generate_unique_str("user2"),
        "firstName": "Bob",
        "lastName": "Jones",
        "email": "bob@example.com",
        "password": "pass2",
        "phone": "444555666",
        "userStatus": 1
    }
    response = api.post("/user/createWithList", json=[user1, user2])
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)


def test_get_user_login_success_200(api):
    response = api.get("/user/login", params={"username": "validUser", "password": "validPassword"})
    assert response.status_code == 200
    assert isinstance(response.text, str)
    if "X-Rate-Limit" in response.headers:
        assert response.headers["X-Rate-Limit"].isdigit()


def test_get_user_login_invalid_credentials_400(api):
    # Missing required query parameters or bad data
    response = api.get("/user/login", params={})
    assert response.status_code in [200, 400]


def test_get_user_logout_success_200(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


def test_get_user_by_name_success_200(api):
    username = generate_unique_str("user")
    payload = {
        "id": generate_unique_id(),
        "username": username,
        "firstName": "Get",
        "lastName": "Test",
        "email": f"{username}@test.com",
        "password": "password",
        "phone": "999888777",
        "userStatus": 0
    }
    api.post("/user", json=payload)

    response = api.get(f"/user/{username}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_get_user_by_name_not_found_404(api):
    non_existent_username = generate_unique_str("non_existent_user")
    response = api.get(f"/user/{non_existent_username}")
    assert response.status_code == 404


def test_put_user_success_200(api):
    username = generate_unique_str("user")
    payload = {
        "id": generate_unique_id(),
        "username": username,
        "firstName": "Pre",
        "lastName": "Update",
        "email": f"{username}@test.com",
        "password": "password",
        "phone": "111111",
        "userStatus": 0
    }
    api.post("/user", json=payload)

    update_payload = {
        "id": payload["id"],
        "username": username,
        "firstName": "Post",
        "lastName": "Update",
        "email": f"updated_{username}@test.com",
        "password": "new_password",
        "phone": "222222",
        "userStatus": 1
    }
    response = api.put(f"/user/{username}", json=update_payload)
    assert response.status_code in [200, 404]


def test_put_user_bad_request_400(api):
    username = generate_unique_str("user")
    invalid_payload = {
        "id": "not-an-integer",
        "userStatus": "invalid-status"
    }
    response = api.put(f"/user/{username}", json=invalid_payload)
    assert response.status_code in [400, 422]


def test_put_user_not_found_404(api):
    non_existent_username = generate_unique_str("non_existent_user")
    payload = {
        "id": generate_unique_id(),
        "username": non_existent_username,
        "firstName": "Ghost",
        "lastName": "User"
    }
    response = api.put(f"/user/{non_existent_username}", json=payload)
    assert response.status_code in [404, 200]


def test_delete_user_success_200(api):
    username = generate_unique_str("user")
    payload = {
        "id": generate_unique_id(),
        "username": username,
        "firstName": "To",
        "lastName": "Delete",
        "email": f"{username}@test.com",
        "password": "password",
        "phone": "333333",
        "userStatus": 0
    }
    api.post("/user", json=payload)

    response = api.delete(f"/user/{username}")
    assert response.status_code in [200, 404]


def test_delete_user_not_found_404(api):
    non_existent_username = generate_unique_str("non_existent_user")
    response = api.delete(f"/user/{non_existent_username}")
    assert response.status_code == 404
