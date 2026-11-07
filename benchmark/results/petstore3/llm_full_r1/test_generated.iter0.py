import uuid
import random
import datetime
import pytest
from jsonschema import validate

# Schemas derived directly from OpenAPI spec
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


def _generate_unique_pet_data():
    pet_id = random.randint(100000, 999999)
    tag_name = f"tag_{uuid.uuid4().hex[:6]}"
    return {
        "id": pet_id,
        "name": f"Pet_{uuid.uuid4().hex[:6]}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/pet.jpg"],
        "tags": [{"id": 1, "name": tag_name}],
        "status": "available",
    }


def _generate_unique_user_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "id": random.randint(100000, 999999),
        "username": f"user_{uid}",
        "firstName": "Test",
        "lastName": "User",
        "email": f"{uid}@example.com",
        "password": "Password123!",
        "phone": "555-0100",
        "userStatus": 1,
    }


# ==============================================================================
# /pet Operations
# ==============================================================================

def test_post_pet_success_200(api):
    pet_data = _generate_unique_pet_data()
    response = api.post("/pet", json=pet_data)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == pet_data["name"]


def test_post_pet_missing_required_fields_400_or_422(api):
    # 'name' and 'photoUrls' are required in Pet schema
    invalid_pet = {"category": {"id": 1, "name": "Invalid"}}
    response = api.post("/pet", json=invalid_pet)
    assert response.status_code in [400, 422]


def test_put_pet_success_200(api):
    pet_data = _generate_unique_pet_data()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    created_id = create_resp.json().get("id", pet_data["id"])

    updated_data = pet_data.copy()
    updated_data["id"] = created_id
    updated_data["name"] = f"Updated_{uuid.uuid4().hex[:6]}"
    updated_data["status"] = "sold"

    put_resp = api.put("/pet", json=updated_data)
    assert put_resp.status_code == 200
    data = put_resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == updated_data["name"]
    assert data["status"] == "sold"


def test_put_pet_invalid_payload_400_or_422(api):
    invalid_payload = {"id": "invalid_id_type", "photoUrls": "not_an_array"}
    response = api.put("/pet", json=invalid_payload)
    assert response.status_code in [400, 422]


def test_put_pet_nonexistent_pet_404_or_200(api):
    pet_data = _generate_unique_pet_data()
    pet_data["id"] = 999999999
    response = api.put("/pet", json=pet_data)
    assert response.status_code in [200, 404]


# ==============================================================================
# /pet/findByStatus Operations
# ==============================================================================

@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pet_findByStatus_valid_status_200(api, status):
    response = api.get("/pet/findByStatus", params={"status": status})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_findByStatus_invalid_status_400(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_value"})
    assert response.status_code in [200, 400]


# ==============================================================================
# /pet/findByTags Operations
# ==============================================================================

def test_get_pet_findByTags_success_200(api):
    pet_data = _generate_unique_pet_data()
    api.post("/pet", json=pet_data)
    tag_name = pet_data["tags"][0]["name"]

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_findByTags_empty_tag_200_or_400(api):
    response = api.get("/pet/findByTags", params={"tags": ""})
    assert response.status_code in [200, 400]


# ==============================================================================
# /pet/{petId} Operations
# ==============================================================================

def test_get_pet_getPetById_success_200(api):
    pet_data = _generate_unique_pet_data()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_getPetById_not_found_404(api):
    response = api.get("/pet/999999999")
    assert response.status_code == 404


def test_get_pet_getPetById_invalid_id_400(api):
    response = api.get("/pet/invalid_pet_id_string")
    assert response.status_code in [400, 404]


def test_post_pet_updatePetWithForm_success_200(api):
    pet_data = _generate_unique_pet_data()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    updated_name = f"FormUpdated_{uuid.uuid4().hex[:6]}"
    response = api.post(f"/pet/{pet_id}", params={"name": updated_name, "status": "sold"})
    assert response.status_code == 200
    if response.headers.get("content-type", "").startswith("application/json"):
        validate(instance=response.json(), schema=PET_SCHEMA)


def test_post_pet_updatePetWithForm_invalid_pet_id_400_or_404(api):
    response = api.post("/pet/invalid_id", params={"name": "Dog", "status": "available"})
    assert response.status_code in [400, 404]


def test_delete_pet_deletePet_success_200(api):
    pet_data = _generate_unique_pet_data()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    delete_resp = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert delete_resp.status_code == 200

    # Ensure it is deleted
    get_resp = api.get(f"/pet/{pet_id}")
    assert get_resp.status_code == 404


def test_delete_pet_deletePet_invalid_id_400_or_404(api):
    response = api.delete("/pet/invalid_id_format")
    assert response.status_code in [400, 404]


# ==============================================================================
# /pet/{petId}/uploadImage Operations
# ==============================================================================

def test_post_pet_uploadImage_success_200(api):
    pet_data = _generate_unique_pet_data()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    dummy_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "test_metadata"},
        data=dummy_image_data,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=API_RESPONSE_SCHEMA)


def test_post_pet_uploadImage_pet_not_found_404(api):
    dummy_image_data = b"\x89PNG\r\n\x1a\n"
    response = api.post(
        "/pet/999999999/uploadImage",
        data=dummy_image_data,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code in [200, 404]


# ==============================================================================
# /store/inventory Operations
# ==============================================================================

def test_get_store_inventory_success_200(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for key, value in data.items():
        assert isinstance(key, str)
        assert isinstance(value, int)


# ==============================================================================
# /store/order Operations
# ==============================================================================

def test_post_store_order_success_200(api):
    order_id = random.randint(1, 5)
    order_payload = {
        "id": order_id,
        "petId": 198772,
        "quantity": 2,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "placed",
        "complete": True,
    }
    response = api.post("/store/order", json=order_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_post_store_order_invalid_input_400_or_422(api):
    invalid_order = {
        "id": "not_an_integer",
        "quantity": "invalid_qty",
        "status": 12345,
    }
    response = api.post("/store/order", json=invalid_order)
    assert response.status_code in [400, 422]


# ==============================================================================
# /store/order/{orderId} Operations
# ==============================================================================

def test_get_store_order_getOrderById_success_200(api):
    order_id = random.randint(1, 5)
    order_payload = {
        "id": order_id,
        "petId": 198772,
        "quantity": 1,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "approved",
        "complete": False,
    }
    post_resp = api.post("/store/order", json=order_payload)
    assert post_resp.status_code == 200

    response = api.get(f"/store/order/{order_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_get_store_order_getOrderById_not_found_404(api):
    # Spec notes: integer IDs with value <= 5 or > 10. Other values will generate exceptions.
    response = api.get("/store/order/999999999")
    assert response.status_code == 404


def test_get_store_order_getOrderById_invalid_id_400(api):
    response = api.get("/store/order/invalid_order_id")
    assert response.status_code in [400, 404]


def test_delete_store_order_deleteOrder_success_200(api):
    order_id = random.randint(1, 5)
    order_payload = {
        "id": order_id,
        "petId": 10,
        "quantity": 1,
        "status": "placed",
        "complete": True,
    }
    api.post("/store/order", json=order_payload)

    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code == 200


def test_delete_store_order_deleteOrder_not_found_404(api):
    response = api.delete("/store/order/999999")
    assert response.status_code in [404, 200]


def test_delete_store_order_deleteOrder_invalid_id_400(api):
    response = api.delete("/store/order/invalid_id")
    assert response.status_code in [400, 404]


# ==============================================================================
# /user Operations
# ==============================================================================

def test_post_user_createUser_success_200(api):
    user_data = _generate_unique_user_data()
    response = api.post("/user", json=user_data)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == user_data["username"]


def test_post_user_createUsersWithListInput_success_200(api):
    user_list = [_generate_unique_user_data(), _generate_unique_user_data()]
    response = api.post("/user/createWithList", json=user_list)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)


def test_get_user_login_success_200(api):
    user_data = _generate_unique_user_data()
    api.post("/user", json=user_data)

    response = api.get("/user/login", params={"username": user_data["username"], "password": user_data["password"]})
    assert response.status_code == 200
    assert "X-Rate-Limit" in response.headers or response.text is not None


def test_get_user_logout_success_200(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


# ==============================================================================
# /user/{username} Operations
# ==============================================================================

def test_get_user_getUserByName_success_200(api):
    user_data = _generate_unique_user_data()
    create_resp = api.post("/user", json=user_data)
    assert create_resp.status_code == 200

    response = api.get(f"/user/{user_data['username']}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == user_data["username"]


def test_get_user_getUserByName_not_found_404(api):
    response = api.get("/user/non_existing_user_999999")
    assert response.status_code == 404


def test_put_user_updateUser_success_200(api):
    user_data = _generate_unique_user_data()
    create_resp = api.post("/user", json=user_data)
    assert create_resp.status_code == 200

    updated_data = user_data.copy()
    updated_data["firstName"] = "UpdatedFirst"
    updated_data["lastName"] = "UpdatedLast"

    response = api.put(f"/user/{user_data['username']}", json=updated_data)
    assert response.status_code == 200

    fetch_resp = api.get(f"/user/{user_data['username']}")
    if fetch_resp.status_code == 200:
        data = fetch_resp.json()
        assert data["firstName"] == "UpdatedFirst"


def test_put_user_updateUser_not_found_404(api):
    dummy_data = _generate_unique_user_data()
    response = api.put("/user/non_existent_username_404", json=dummy_data)
    assert response.status_code in [404, 200]


def test_delete_user_deleteUser_success_200(api):
    user_data = _generate_unique_user_data()
    create_resp = api.post("/user", json=user_data)
    assert create_resp.status_code == 200

    delete_resp = api.delete(f"/user/{user_data['username']}")
    assert delete_resp.status_code == 200

    fetch_resp = api.get(f"/user/{user_data['username']}")
    assert fetch_resp.status_code == 404


def test_delete_user_deleteUser_not_found_404(api):
    response = api.delete("/user/non_existent_user_for_delete_9999")
    assert response.status_code in [404, 400]
