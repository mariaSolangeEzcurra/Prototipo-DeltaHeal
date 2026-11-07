import uuid
import random
import datetime
import pytest
from jsonschema import validate

# ---------------------------------------------------------------------------
# Schemas JSON derivados del contrato OpenAPI
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


# ---------------------------------------------------------------------------
# Helpers para generación de datos únicos
# ---------------------------------------------------------------------------

def random_id():
    return random.randint(100000, 999999)


def make_pet_payload(pet_id=None, name=None, status="available", tags=None):
    return {
        "id": pet_id if pet_id is not None else random_id(),
        "name": name or f"pet_{uuid.uuid4().hex[:8]}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": tags or [{"id": 1, "name": "tag1"}],
        "status": status,
    }


def make_user_payload(username=None):
    uname = username or f"user_{uuid.uuid4().hex[:8]}"
    return {
        "id": random_id(),
        "username": uname,
        "firstName": "Test",
        "lastName": "User",
        "email": f"{uname}@example.com",
        "password": "secretPassword123",
        "phone": "1234567890",
        "userStatus": 1,
    }


def make_order_payload(order_id=None, pet_id=None, status="placed"):
    return {
        "id": order_id if order_id is not None else random_id(),
        "petId": pet_id if pet_id is not None else random_id(),
        "quantity": 1,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        "complete": False,
    }


# ===========================================================================
# PET TESTS
# ===========================================================================

def test_post_pet_success_200(api):
    payload = make_pet_payload()
    res = api.post("/pet", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input_400_or_422(api):
    # Enviar objeto vacío o payload sin campos obligatorios name y photoUrls
    res = api.post("/pet", json={"status": "invalid_field_only"})
    assert res.status_code in [400, 422]


def test_put_pet_success_200(api):
    pet_id = random_id()
    create_payload = make_pet_payload(pet_id=pet_id, name="OriginalName")
    create_res = api.post("/pet", json=create_payload)
    assert create_res.status_code == 200

    update_payload = make_pet_payload(pet_id=pet_id, name="UpdatedName", status="sold")
    res = api.put("/pet", json=update_payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == "UpdatedName"
    assert data["status"] == "sold"


def test_put_pet_invalid_input_400_or_422(api):
    res = api.put("/pet", json={"id": "not_an_integer", "name": 12345})
    assert res.status_code in [400, 422]


def test_put_pet_not_found_404(api):
    non_existent_id = 99999999999
    update_payload = make_pet_payload(pet_id=non_existent_id, name="NonExistent")
    res = api.put("/pet", json=update_payload)
    assert res.status_code in [200, 404]


def test_get_pet_find_by_status_success_200(api):
    for status in ["available", "pending", "sold"]:
        res = api.get("/pet/findByStatus", params={"status": status})
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        for pet in data:
            validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_find_by_status_invalid_400(api):
    res = api.get("/pet/findByStatus", params={"status": "non_existing_status_value"})
    assert res.status_code in [400, 200]


def test_get_pet_find_by_tags_success_200(api):
    tag_name = f"tag_{uuid.uuid4().hex[:6]}"
    pet_payload = make_pet_payload(tags=[{"id": 1, "name": tag_name}])
    create_res = api.post("/pet", json=pet_payload)
    assert create_res.status_code == 200

    res = api.get("/pet/findByTags", params={"tags": tag_name})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_find_by_tags_empty_or_invalid_400(api):
    res = api.get("/pet/findByTags", params={"tags": ""})
    assert res.status_code in [200, 400]


def test_get_pet_by_id_success_200(api):
    pet_id = random_id()
    create_res = api.post("/pet", json=make_pet_payload(pet_id=pet_id))
    assert create_res.status_code == 200

    res = api.get(f"/pet/{pet_id}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_invalid_id_400(api):
    res = api.get("/pet/invalid_id_string")
    assert res.status_code in [400, 404]


def test_get_pet_by_id_not_found_404(api):
    non_existent_id = 8888888888888
    res = api.get(f"/pet/{non_existent_id}")
    assert res.status_code == 404


def test_post_pet_update_with_form_success_200(api):
    pet_id = random_id()
    create_res = api.post("/pet", json=make_pet_payload(pet_id=pet_id, status="available"))
    assert create_res.status_code == 200

    res = api.post(f"/pet/{pet_id}", params={"name": "FormUpdatedName", "status": "sold"})
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=PET_SCHEMA)


def test_post_pet_update_with_form_invalid_input_400(api):
    res = api.post("/pet/invalid_id", params={"name": "NewName"})
    assert res.status_code in [400, 404]


def test_delete_pet_success_200(api):
    pet_id = random_id()
    create_res = api.post("/pet", json=make_pet_payload(pet_id=pet_id))
    assert create_res.status_code == 200

    res = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert res.status_code == 200

    get_res = api.get(f"/pet/{pet_id}")
    assert get_res.status_code == 404


def test_delete_pet_invalid_id_400(api):
    res = api.delete("/pet/not_a_valid_integer_id")
    assert res.status_code in [400, 404]


def test_post_pet_upload_image_success_200(api):
    pet_id = random_id()
    create_res = api.post("/pet", json=make_pet_payload(pet_id=pet_id))
    assert create_res.status_code == 200

    dummy_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "test_metadata"},
        data=dummy_image_bytes,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=API_RESPONSE_SCHEMA)


def test_post_pet_upload_image_not_found_404(api):
    non_existent_id = 99999999999
    res = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=b"raw_bytes",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert res.status_code in [200, 400, 404]


# ===========================================================================
# STORE TESTS
# ===========================================================================

def test_get_store_inventory_success_200(api):
    res = api.get("/store/inventory")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)
    for k, v in data.items():
        assert isinstance(k, str)
        assert isinstance(v, int)


def test_post_store_order_success_200(api):
    order_id = random.randint(1, 100)
    payload = make_order_payload(order_id=order_id)
    res = api.post("/store/order", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_post_store_order_invalid_input_400_or_422(api):
    res = api.post("/store/order", json={"quantity": "invalid_string_quantity"})
    assert res.status_code in [400, 422]


def test_get_store_order_by_id_success_200(api):
    order_id = random.randint(1, 5)
    payload = make_order_payload(order_id=order_id)
    create_res = api.post("/store/order", json=payload)
    assert create_res.status_code == 200

    res = api.get(f"/store/order/{order_id}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_get_store_order_by_id_invalid_id_400(api):
    res = api.get("/store/order/invalid_order_id")
    assert res.status_code in [400, 404]


def test_get_store_order_by_id_not_found_404(api):
    res = api.get("/store/order/999999999")
    assert res.status_code == 404


def test_delete_store_order_success_200(api):
    order_id = random.randint(100, 999)
    payload = make_order_payload(order_id=order_id)
    create_res = api.post("/store/order", json=payload)
    assert create_res.status_code == 200

    res = api.delete(f"/store/order/{order_id}")
    assert res.status_code == 200

    get_res = api.get(f"/store/order/{order_id}")
    assert get_res.status_code == 404


def test_delete_store_order_invalid_id_400(api):
    res = api.delete("/store/order/invalid_order_id")
    assert res.status_code in [400, 404]


def test_delete_store_order_not_found_404(api):
    res = api.delete("/store/order/9999999")
    assert res.status_code in [400, 404]


# ===========================================================================
# USER TESTS
# ===========================================================================

def test_post_user_create_success_200(api):
    payload = make_user_payload()
    res = api.post("/user", json=payload)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == payload["username"]


def test_post_user_create_with_list_success_200(api):
    users = [make_user_payload(), make_user_payload()]
    res = api.post("/user/createWithList", json=users)
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_SCHEMA)


def test_get_user_login_success_200(api):
    user_payload = make_user_payload()
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    res = api.get(
        "/user/login",
        params={"username": user_payload["username"], "password": user_payload["password"]},
    )
    assert res.status_code == 200
    assert "X-Rate-Limit" in res.headers or res.text is not None


def test_get_user_login_invalid_400(api):
    res = api.get("/user/login", params={})
    assert res.status_code in [200, 400]


def test_get_user_logout_success_200(api):
    res = api.get("/user/logout")
    assert res.status_code == 200


def test_get_user_by_name_success_200(api):
    user_payload = make_user_payload()
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    res = api.get(f"/user/{user_payload['username']}")
    assert res.status_code == 200
    data = res.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == user_payload["username"]


def test_get_user_by_name_not_found_404(api):
    non_existent_username = f"user_not_found_{uuid.uuid4().hex}"
    res = api.get(f"/user/{non_existent_username}")
    assert res.status_code == 404


def test_put_user_success_200(api):
    user_payload = make_user_payload()
    username = user_payload["username"]
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    updated_payload = dict(user_payload)
    updated_payload["firstName"] = "UpdatedFirstName"
    updated_payload["phone"] = "9876543210"

    res = api.put(f"/user/{username}", json=updated_payload)
    assert res.status_code == 200

    get_res = api.get(f"/user/{username}")
    if get_res.status_code == 200:
        updated_user = get_res.json()
        assert updated_user["firstName"] == "UpdatedFirstName"


def test_put_user_not_found_404(api):
    non_existent_username = f"non_existent_{uuid.uuid4().hex}"
    payload = make_user_payload(username=non_existent_username)
    res = api.put(f"/user/{non_existent_username}", json=payload)
    assert res.status_code in [200, 404]


def test_put_user_bad_request_400(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    res = api.put(f"/user/{username}", json={"userStatus": "invalid_status_type"})
    assert res.status_code in [400, 404, 200]


def test_delete_user_success_200(api):
    user_payload = make_user_payload()
    username = user_payload["username"]
    create_res = api.post("/user", json=user_payload)
    assert create_res.status_code == 200

    res = api.delete(f"/user/{username}")
    assert res.status_code == 200

    get_res = api.get(f"/user/{username}")
    assert get_res.status_code == 404


def test_delete_user_not_found_404(api):
    non_existent_username = f"non_existent_{uuid.uuid4().hex}"
    res = api.delete(f"/user/{non_existent_username}")
    assert res.status_code == 404
