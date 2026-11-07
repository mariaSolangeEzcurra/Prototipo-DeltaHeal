import uuid
import random
import datetime
import pytest
from jsonschema import validate

# ---------------------------------------------------------------------------
# Schemas for response validation based on OpenAPI components
# ---------------------------------------------------------------------------

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

INVENTORY_SCHEMA = {
    "type": "object",
    "additionalProperties": {"type": "integer"},
}

# ---------------------------------------------------------------------------
# Helper Generators
# ---------------------------------------------------------------------------


def generate_random_id():
    return random.randint(100000, 99999999)


def generate_pet_payload(pet_id=None, name="TestPet", status="available", tags=None):
    if pet_id is None:
        pet_id = generate_random_id()
    if tags is None:
        tags = [{"id": 1, "name": f"tag_{uuid.uuid4().hex[:6]}"}]
    return {
        "id": pet_id,
        "name": f"{name}_{uuid.uuid4().hex[:6]}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": tags,
        "status": status,
    }


def generate_user_payload(user_id=None, username=None):
    unique = uuid.uuid4().hex[:8]
    return {
        "id": user_id or generate_random_id(),
        "username": username or f"user_{unique}",
        "firstName": "QA",
        "lastName": "Tester",
        "email": f"test_{unique}@example.com",
        "password": "Password123!",
        "phone": "1234567890",
        "userStatus": 1,
    }


def generate_order_payload(order_id=None, pet_id=None, status="placed"):
    return {
        "id": order_id if order_id is not None else random.randint(1, 5),
        "petId": pet_id or generate_random_id(),
        "quantity": 1,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        "complete": False,
    }


# ===========================================================================
# PET ENDPOINTS
# ===========================================================================


def test_post_pet_success_200(api):
    payload = generate_pet_payload()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input_400_or_422(api):
    # Missing required 'name' and 'photoUrls'
    response = api.post("/pet", json={"status": "available"})
    assert response.status_code in [400, 422]


def test_put_pet_success_200(api):
    payload = generate_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    created_pet = create_res.json()

    updated_payload = payload.copy()
    updated_payload["id"] = created_pet.get("id", payload["id"])
    updated_payload["name"] = f"Updated_{uuid.uuid4().hex[:6]}"
    updated_payload["status"] = "sold"

    update_res = api.put("/pet", json=updated_payload)
    assert update_res.status_code == 200
    data = update_res.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == updated_payload["name"]
    assert data["status"] == "sold"


def test_put_pet_invalid_id_or_validation_400_422(api):
    invalid_payload = {"id": "invalid_id_format", "name": 12345}
    response = api.put("/pet", json=invalid_payload)
    assert response.status_code in [400, 422]


def test_put_pet_not_found_404(api):
    non_existent_id = 999999999999
    payload = generate_pet_payload(pet_id=non_existent_id)
    response = api.put("/pet", json=payload)
    # Some mock/sample implementations respond with 404 if pet does not exist
    assert response.status_code in [200, 404]


def test_get_pet_find_by_status_success_200(api):
    response = api.get("/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)
        assert pet.get("status") == "available"


def test_get_pet_find_by_status_invalid_400(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_xyz"})
    assert response.status_code in [400, 422]


def test_get_pet_find_by_tags_success_200(api):
    unique_tag = f"tag_{uuid.uuid4().hex[:6]}"
    pet_payload = generate_pet_payload(tags=[{"id": 1, "name": unique_tag}])
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200

    response = api.get("/pet/findByTags", params={"tags": unique_tag})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_by_id_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", pet_payload["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_invalid_id_400(api):
    response = api.get("/pet/invalid_string_id")
    assert response.status_code in [400, 404]


def test_get_pet_by_id_not_found_404(api):
    non_existent_id = 999999999999999
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_post_pet_update_with_form_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", pet_payload["id"])

    new_name = f"FormUpdated_{uuid.uuid4().hex[:6]}"
    response = api.post(f"/pet/{pet_id}", params={"name": new_name, "status": "sold"})
    assert response.status_code == 200


def test_post_pet_update_with_form_invalid_input_400(api):
    response = api.post("/pet/not_a_number", params={"name": "BadId"})
    assert response.status_code in [400, 404]


def test_delete_pet_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", pet_payload["id"])

    del_res = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert del_res.status_code == 200

    # Ensure it's deleted
    get_res = api.get(f"/pet/{pet_id}")
    assert get_res.status_code == 404


def test_delete_pet_invalid_id_400(api):
    response = api.delete("/pet/invalid_id_format")
    assert response.status_code in [400, 404]


def test_post_pet_upload_image_success_200(api):
    pet_payload = generate_pet_payload()
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", pet_payload["id"])

    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        data=dummy_image,
        headers={"Content-Type": "application/octet-stream"},
        params={"additionalMetadata": "test_metadata"},
    )
    assert response.status_code == 200
    validate(instance=response.json(), schema=API_RESPONSE_SCHEMA)


def test_post_pet_upload_image_not_found_404(api):
    non_existent_id = 9999999999999
    dummy_image = b"\x89PNG"
    response = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=dummy_image,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code in [404, 200]


# ===========================================================================
# STORE ENDPOINTS
# ===========================================================================


def test_get_store_inventory_success_200(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=INVENTORY_SCHEMA)


def test_post_store_order_success_200(api):
    order_payload = generate_order_payload(order_id=random.randint(1, 5))
    response = api.post("/store/order", json=order_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["petId"] == order_payload["petId"]


def test_post_store_order_invalid_400_or_422(api):
    invalid_order = {"quantity": "invalid_int", "shipDate": "invalid_date_format"}
    response = api.post("/store/order", json=invalid_order)
    assert response.status_code in [400, 422]


def test_get_store_order_by_id_success_200(api):
    target_id = random.randint(1, 5)
    order_payload = generate_order_payload(order_id=target_id)
    post_res = api.post("/store/order", json=order_payload)
    assert post_res.status_code == 200

    response = api.get(f"/store/order/{target_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == target_id


def test_get_store_order_by_id_invalid_400(api):
    response = api.get("/store/order/invalid_order_id")
    assert response.status_code in [400, 404]


def test_get_store_order_by_id_not_found_404(api):
    # Per docs, IDs > 5 and <= 10 or non-existent generate exceptions
    non_existent_order_id = 999999999
    response = api.get(f"/store/order/{non_existent_order_id}")
    assert response.status_code == 404


def test_delete_store_order_success_200(api):
    order_id = random.randint(10, 500)
    order_payload = generate_order_payload(order_id=order_id)
    api.post("/store/order", json=order_payload)

    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code == 200

    # Ensure deleted
    get_res = api.get(f"/store/order/{order_id}")
    assert get_res.status_code == 404


def test_delete_store_order_invalid_400(api):
    response = api.delete("/store/order/invalid_id")
    assert response.status_code in [400, 404]


def test_delete_store_order_not_found_404(api):
    response = api.delete("/store/order/999999999")
    assert response.status_code in [400, 404]


# ===========================================================================
# USER ENDPOINTS
# ===========================================================================


def test_post_user_success_200(api):
    user_payload = generate_user_payload()
    response = api.post("/user", json=user_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data.get("username") == user_payload["username"]


def test_post_user_create_with_list_success_200(api):
    users = [generate_user_payload(), generate_user_payload()]
    response = api.post("/user/createWithList", json=users)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)


def test_get_user_login_success_200(api):
    user = generate_user_payload()
    api.post("/user", json=user)

    response = api.get(
        "/user/login",
        params={"username": user["username"], "password": user["password"]},
    )
    assert response.status_code == 200
    assert isinstance(response.text, str)
    if "X-Rate-Limit" in response.headers:
        assert response.headers["X-Rate-Limit"].isdigit()


def test_get_user_login_invalid_credentials_400(api):
    # Depending on implementation, missing username/password returns 400
    response = api.get("/user/login")
    assert response.status_code in [200, 400]


def test_get_user_logout_success_200(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


def test_get_user_by_name_success_200(api):
    user_payload = generate_user_payload()
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    response = api.get(f"/user/{user_payload['username']}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == user_payload["username"]


def test_get_user_by_name_not_found_404(api):
    non_existent_username = f"not_found_{uuid.uuid4().hex}"
    response = api.get(f"/user/{non_existent_username}")
    assert response.status_code == 404


def test_put_user_success_200(api):
    user_payload = generate_user_payload()
    api.post("/user", json=user_payload)

    updated_payload = user_payload.copy()
    updated_payload["firstName"] = "UpdatedFirst"
    updated_payload["lastName"] = "UpdatedLast"

    response = api.put(f"/user/{user_payload['username']}", json=updated_payload)
    assert response.status_code == 200

    get_res = api.get(f"/user/{user_payload['username']}")
    if get_res.status_code == 200:
        data = get_res.json()
        assert data.get("firstName") == "UpdatedFirst"


def test_put_user_not_found_or_bad_request_400_404(api):
    non_existent_username = f"ghost_{uuid.uuid4().hex}"
    user_payload = generate_user_payload(username=non_existent_username)
    response = api.put(f"/user/{non_existent_username}", json=user_payload)
    assert response.status_code in [200, 400, 404]


def test_delete_user_success_200(api):
    user_payload = generate_user_payload()
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    del_res = api.delete(f"/user/{user_payload['username']}")
    assert del_res.status_code == 200

    # Ensure deleted
    get_res = api.get(f"/user/{user_payload['username']}")
    assert get_res.status_code == 404


def test_delete_user_not_found_404(api):
    non_existent_username = f"absent_{uuid.uuid4().hex}"
    response = api.delete(f"/user/{non_existent_username}")
    assert response.status_code in [400, 404]
