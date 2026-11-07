import datetime
import random
import string
import uuid
import jsonschema
import pytest

SCHEMA_PET = {
    "type": "object",
    "required": ["name", "photoUrls"],
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "category": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        },
        "photoUrls": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        },
        "status": {
            "type": "string",
            "enum": ["available", "pending", "sold"],
        },
    },
}

SCHEMA_ORDER = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "petId": {"type": "integer"},
        "quantity": {"type": "integer"},
        "shipDate": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["placed", "approved", "delivered"],
        },
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


def _random_int(min_val=100000, max_val=999999):
    return random.randint(min_val, max_val)


def _random_str(length=8):
    return "".join(random.choices(string.ascii_letters, k=length))


def _generate_pet_payload(pet_id=None, name=None, status="available", tags=None):
    return {
        "id": pet_id or _random_int(),
        "name": name or f"pet_{_random_str()}",
        "category": {"id": _random_int(1, 100), "name": f"cat_{_random_str()}"},
        "photoUrls": [f"https://example.com/photos/{_random_str()}.jpg"],
        "tags": tags or [{"id": _random_int(1, 100), "name": f"tag_{_random_str()}"}],
        "status": status,
    }


def _generate_user_payload(user_id=None, username=None):
    u_name = username or f"user_{_random_str()}"
    return {
        "id": user_id or _random_int(),
        "username": u_name,
        "firstName": "John",
        "lastName": "Doe",
        "email": f"{u_name}@example.com",
        "password": "Password123!",
        "phone": "555-0199",
        "userStatus": 1,
    }


def _generate_order_payload(order_id=None, pet_id=None, status="placed"):
    return {
        "id": order_id if order_id is not None else _random_int(1, 5),
        "petId": pet_id or _random_int(),
        "quantity": random.randint(1, 10),
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status,
        "complete": False,
    }


# ==========================================
# /pet tests
# ==========================================

def test_post_pet_success(api):
    payload = _generate_pet_payload()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input(api):
    # Missing required 'name' and 'photoUrls'
    payload = {"status": "available"}
    response = api.post("/pet", json=payload)
    assert response.status_code in [400, 422]


def test_put_pet_success(api):
    initial_payload = _generate_pet_payload()
    create_resp = api.post("/pet", json=initial_payload)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", initial_payload["id"])

    updated_payload = _generate_pet_payload(pet_id=pet_id, name="updated_name", status="sold")
    put_resp = api.put("/pet", json=updated_payload)
    assert put_resp.status_code == 200
    data = put_resp.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)
    assert data["id"] == pet_id
    assert data["name"] == "updated_name"
    assert data["status"] == "sold"


def test_put_pet_invalid_input(api):
    payload = {"id": "invalid_id_format", "name": 12345}
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 404, 422]


# ==========================================
# /pet/findByStatus tests
# ==========================================

@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pet_findByStatus_success(api, status):
    # Ensure at least one pet exists with target status
    api.post("/pet", json=_generate_pet_payload(status=status))

    response = api.get("/pet/findByStatus", params={"status": status})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for item in data:
        jsonschema.validate(instance=item, schema=SCHEMA_PET)
        assert item.get("status") == status


def test_get_pet_findByStatus_invalid(api):
    response = api.get("/pet/findByStatus", params={"status": "not_a_valid_status"})
    assert response.status_code == 400


# ==========================================
# /pet/findByTags tests
# ==========================================

def test_get_pet_findByTags_success(api):
    tag_name = f"tag_{_random_str()}"
    pet_payload = _generate_pet_payload(tags=[{"id": _random_int(1, 100), "name": tag_name}])
    api.post("/pet", json=pet_payload)

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for item in data:
        jsonschema.validate(instance=item, schema=SCHEMA_PET)


def test_get_pet_findByTags_empty(api):
    response = api.get("/pet/findByTags", params={"tags": ""})
    assert response.status_code in [200, 400]


# ==========================================
# /pet/{petId} tests
# ==========================================

def test_get_pet_by_id_success(api):
    payload = _generate_pet_payload()
    create_resp = api.post("/pet", json=payload)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", payload["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_PET)
    assert data["id"] == pet_id


def test_get_pet_by_id_not_found(api):
    non_existent_id = _random_int(900000, 999999)
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_get_pet_by_id_invalid_id(api):
    response = api.get("/pet/invalid-id-format")
    assert response.status_code == 400


def test_post_pet_update_with_form_success(api):
    payload = _generate_pet_payload()
    create_resp = api.post("/pet", json=payload)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", payload["id"])

    new_name = f"form_pet_{_random_str()}"
    response = api.post(f"/pet/{pet_id}", params={"name": new_name, "status": "sold"})
    assert response.status_code == 200
    if response.headers.get("content-type", "").startswith("application/json"):
        data = response.json()
        jsonschema.validate(instance=data, schema=SCHEMA_PET)


def test_post_pet_update_with_form_invalid_id(api):
    response = api.post("/pet/invalid-id-format", params={"name": "test"})
    assert response.status_code in [400, 404]


def test_delete_pet_success(api):
    payload = _generate_pet_payload()
    create_resp = api.post("/pet", json=payload)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", payload["id"])

    response = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert response.status_code == 200

    get_resp = api.get(f"/pet/{pet_id}")
    assert get_resp.status_code == 404


def test_delete_pet_invalid_id(api):
    response = api.delete("/pet/invalid-string-id")
    assert response.status_code in [400, 404]


# ==========================================
# /pet/{petId}/uploadImage tests
# ==========================================

def test_post_upload_image_success(api):
    payload = _generate_pet_payload()
    create_resp = api.post("/pet", json=payload)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", payload["id"])

    fake_image_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        params={"additionalMetadata": "profile_pic"},
        data=fake_image_bytes,
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_API_RESPONSE)


def test_post_upload_image_not_found(api):
    non_existent_id = _random_int(900000, 999999)
    response = api.post(
        f"/pet/{non_existent_id}/uploadImage",
        data=b"test data",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code in [400, 404]


# ==========================================
# /store/inventory tests
# ==========================================

def test_get_store_inventory_success(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for val in data.values():
        assert isinstance(val, int)


# ==========================================
# /store/order tests
# ==========================================

def test_post_store_order_success(api):
    pet_payload = _generate_pet_payload()
    pet_resp = api.post("/pet", json=pet_payload)
    assert pet_resp.status_code == 200
    pet_id = pet_resp.json().get("id", pet_payload["id"])

    order_payload = _generate_order_payload(order_id=_random_int(1, 5), pet_id=pet_id)
    response = api.post("/store/order", json=order_payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_ORDER)
    assert data["petId"] == pet_id
    assert data["status"] == order_payload["status"]


def test_post_store_order_invalid(api):
    invalid_order = {"id": "invalid_id", "petId": "invalid_pet", "quantity": "bad"}
    response = api.post("/store/order", json=invalid_order)
    assert response.status_code in [400, 422]


# ==========================================
# /store/order/{orderId} tests
# ==========================================

def test_get_store_order_by_id_success(api):
    order_id = _random_int(1, 5)
    order_payload = _generate_order_payload(order_id=order_id)
    create_resp = api.post("/store/order", json=order_payload)
    assert create_resp.status_code == 200

    response = api.get(f"/store/order/{order_id}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_ORDER)
    assert data["id"] == order_id


def test_get_store_order_by_id_not_found(api):
    # Values between 6 and 10 generate not found per spec docs
    response = api.get("/store/order/9")
    assert response.status_code == 404


def test_get_store_order_by_id_invalid(api):
    response = api.get("/store/order/invalid_order_id")
    assert response.status_code == 400


def test_delete_store_order_success(api):
    order_id = _random_int(1, 5)
    order_payload = _generate_order_payload(order_id=order_id)
    api.post("/store/order", json=order_payload)

    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code == 200

    get_resp = api.get(f"/store/order/{order_id}")
    assert get_resp.status_code == 404


def test_delete_store_order_not_found(api):
    response = api.delete(f"/store/order/{_random_int(99000, 99999)}")
    assert response.status_code in [404, 400]


def test_delete_store_order_invalid(api):
    response = api.delete("/store/order/invalid_id")
    assert response.status_code == 400


# ==========================================
# /user tests
# ==========================================

def test_post_user_create_success(api):
    payload = _generate_user_payload()
    response = api.post("/user", json=payload)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)
    assert data["username"] == payload["username"]


def test_post_user_create_with_list_success(api):
    users = [_generate_user_payload(), _generate_user_payload()]
    response = api.post("/user/createWithList", json=users)
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)


# ==========================================
# /user/login and /user/logout tests
# ==========================================

def test_get_user_login_success(api):
    response = api.get("/user/login", params={"username": "testuser", "password": "password123"})
    assert response.status_code == 200
    assert isinstance(response.text, str)


def test_get_user_logout_success(api):
    response = api.get("/user/logout")
    assert response.status_code == 200


# ==========================================
# /user/{username} tests
# ==========================================

def test_get_user_by_username_success(api):
    payload = _generate_user_payload()
    create_resp = api.post("/user", json=payload)
    assert create_resp.status_code == 200

    response = api.get(f"/user/{payload['username']}")
    assert response.status_code == 200
    data = response.json()
    jsonschema.validate(instance=data, schema=SCHEMA_USER)
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]


def test_get_user_by_username_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    response = api.get(f"/user/{non_existent_username}")
    assert response.status_code == 404


def test_put_user_success(api):
    payload = _generate_user_payload()
    create_resp = api.post("/user", json=payload)
    assert create_resp.status_code == 200

    payload["firstName"] = "UpdatedName"
    payload["lastName"] = "UpdatedLastname"
    response = api.put(f"/user/{payload['username']}", json=payload)
    assert response.status_code == 200

    get_resp = api.get(f"/user/{payload['username']}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["firstName"] == "UpdatedName"


def test_put_user_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    payload = _generate_user_payload(username=non_existent_username)
    response = api.put(f"/user/{non_existent_username}", json=payload)
    assert response.status_code in [400, 404]


def test_delete_user_success(api):
    payload = _generate_user_payload()
    create_resp = api.post("/user", json=payload)
    assert create_resp.status_code == 200

    response = api.delete(f"/user/{payload['username']}")
    assert response.status_code == 200

    get_resp = api.get(f"/user/{payload['username']}")
    assert get_resp.status_code == 404


def test_delete_user_not_found(api):
    non_existent_username = f"nonexistent_{uuid.uuid4().hex}"
    response = api.delete(f"/user/{non_existent_username}")
    assert response.status_code == 404
