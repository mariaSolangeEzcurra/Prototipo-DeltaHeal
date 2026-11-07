import uuid
import random
import datetime
import pytest
from jsonschema import validate

# Schemas derived from OpenAPI contract
PET_SCHEMA = {
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
# PET OPERATIONS
# ---------------------------------------------------------------------------

def test_post_pet_success(api):
    payload = {
        "id": random.randint(100000, 999999),
        "name": f"Doggo_{uuid.uuid4().hex[:6]}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/pet.jpg"],
        "tags": [{"id": 1, "name": "tag1"}],
        "status": "available",
    }
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]


def test_post_pet_missing_required_fields(api):
    # 'name' and 'photoUrls' are required by schema
    payload = {"status": "available"}
    response = api.post("/pet", json=payload)
    assert response.status_code in [400, 422]


def test_put_pet_success(api):
    pet_id = random.randint(100000, 999999)
    initial_payload = {
        "id": pet_id,
        "name": "InitialPet",
        "photoUrls": ["https://example.com/initial.jpg"],
        "status": "available",
    }
    api.post("/pet", json=initial_payload)

    updated_payload = {
        "id": pet_id,
        "name": "UpdatedPet",
        "photoUrls": ["https://example.com/updated.jpg"],
        "status": "sold",
    }
    response = api.put("/pet", json=updated_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == "UpdatedPet"
    assert data["status"] == "sold"


def test_put_pet_missing_required_fields(api):
    payload = {"id": random.randint(100000, 999999)}
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 404, 422]


def test_get_pet_by_id_success(api):
    pet_id = random.randint(100000, 999999)
    payload = {
        "id": pet_id,
        "name": "SearchablePet",
        "photoUrls": ["https://example.com/pet.jpg"],
        "status": "available",
    }
    create_resp = api.post("/pet", json=payload)
    assert create_resp.status_code == 200

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_invalid_id(api):
    response = api.get("/pet/invalid_id_format")
    assert response.status_code == 400


def test_get_pet_by_id_not_found(api):
    non_existent_id = 99999999999999
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_get_pet_find_by_status_valid(api):
    response = api.get("/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_get_pet_find_by_status_invalid(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_xyz"})
    assert response.status_code == 400


def test_get_pet_find_by_tags_valid(api):
    tag = f"tag_{uuid.uuid4().hex[:6]}"
    pet_payload = {
        "id": random.randint(100000, 999999),
        "name": "TaggedPet",
        "photoUrls": ["https://example.com/pet.jpg"],
        "tags": [{"id": 1, "name": tag}],
        "status": "available",
    }
    api.post("/pet", json=pet_payload)

    response = api.get("/pet/findByTags", params={"tags": tag})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)


def test_post_pet_update_with_form_success(api):
    pet_id = random.randint(100000, 999999)
    payload = {
        "id": pet_id,
        "name": "PreFormPet",
        "photoUrls": ["https://example.com/pet.jpg"],
        "status": "available",
    }
    api.post("/pet", json=payload)

    new_name = f"PostFormPet_{uuid.uuid4().hex[:4]}"
    response = api.post(f"/pet/{pet_id}", params={"name": new_name, "status": "sold"})
    assert response.status_code == 200


def test_post_pet_update_with_form_invalid_id(api):
    response = api.post("/pet/not_an_int", params={"name": "test", "status": "sold"})
    assert response.status_code == 400


def test_post_pet_upload_image_success(api):
    pet_id = random.randint(100000, 999999)
    pet_payload = {
        "id": pet_id,
        "name": "ImagePet",
        "photoUrls": [],
        "status": "available",
    }
    api.post("/pet", json=pet_payload)

    fake_binary = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        f"/pet/{pet_id}/uploadImage",
        data=fake_binary,
        headers=headers,
        params={"additionalMetadata": "profile picture"},
    )
    assert response.status_code == 200
    validate(instance=response.json(), schema=API_RESPONSE_SCHEMA)


def test_post_pet_upload_image_not_found(api):
    fake_binary = b"\x00\x01\x02"
    headers = {"Content-Type": "application/octet-stream"}
    response = api.post(
        "/pet/99999999999999/uploadImage",
        data=fake_binary,
        headers=headers,
    )
    assert response.status_code in [400, 404]


def test_delete_pet_success(api):
    pet_id = random.randint(100000, 999999)
    payload = {
        "id": pet_id,
        "name": "PetToDelete",
        "photoUrls": ["https://example.com/pet.jpg"],
        "status": "available",
    }
    api.post("/pet", json=payload)

    response = api.delete(f"/pet/{pet_id}", headers={"api_key": "special-key"})
    assert response.status_code == 200


def test_delete_pet_invalid_id(api):
    response = api.delete("/pet/invalid_pet_id_format")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# STORE OPERATIONS
# ---------------------------------------------------------------------------

def test_get_store_inventory_success(api):
    response = api.get("/store/inventory")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    for key, value in data.items():
        assert isinstance(key, str)
        assert isinstance(value, int)


def test_post_store_order_success(api):
    order_id = random.randint(1, 5)
    payload = {
        "id": order_id,
        "petId": 10,
        "quantity": 2,
        "shipDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "placed",
        "complete": True,
    }
    response = api.post("/store/order", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_post_store_order_invalid(api):
    payload = {"quantity": "invalid_quantity_type"}
    response = api.post("/store/order", json=payload)
    assert response.status_code in [400, 422]


def test_get_store_order_by_id_success(api):
    order_id = random.randint(1, 5)
    payload = {
        "id": order_id,
        "petId": 10,
        "quantity": 1,
        "status": "placed",
        "complete": False,
    }
    api.post("/store/order", json=payload)

    response = api.get(f"/store/order/{order_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=ORDER_SCHEMA)
    assert data["id"] == order_id


def test_get_store_order_by_id_invalid(api):
    response = api.get("/store/order/invalid_order_id")
    assert response.status_code == 400


def test_get_store_order_by_id_not_found(api):
    response = api.get("/store/order/99999999")
    assert response.status_code == 404


def test_delete_store_order_success(api):
    order_id = random.randint(1, 5)
    payload = {
        "id": order_id,
        "petId": 10,
        "quantity": 1,
        "status": "placed",
    }
    api.post("/store/order", json=payload)

    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code == 200


def test_delete_store_order_invalid(api):
    response = api.delete("/store/order/invalid_id")
    assert response.status_code == 400


def test_delete_store_order_not_found(api):
    response = api.delete("/store/order/99999999")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# USER OPERATIONS
# ---------------------------------------------------------------------------

def test_post_user_success(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": random.randint(1000, 9999),
        "username": username,
        "firstName": "Jane",
        "lastName": "Doe",
        "email": f"{username}@example.com",
        "password": "securePass123",
        "phone": "555-1234",
        "userStatus": 1,
    }
    response = api.post("/user", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_post_user_create_with_list_success(api):
    u1 = f"user_{uuid.uuid4().hex[:8]}"
    u2 = f"user_{uuid.uuid4().hex[:8]}"
    payload = [
        {
            "id": random.randint(1000, 4999),
            "username": u1,
            "firstName": "UserOne",
            "lastName": "Test",
            "email": f"{u1}@example.com",
            "password": "pass",
            "phone": "111",
            "userStatus": 1,
        },
        {
            "id": random.randint(5000, 9999),
            "username": u2,
            "firstName": "UserTwo",
            "lastName": "Test",
            "email": f"{u2}@example.com",
            "password": "pass",
            "phone": "222",
            "userStatus": 1,
        },
    ]
    response = api.post("/user/createWithList", json=payload)
    assert response.status_code == 200


def test_get_user_by_name_success(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": random.randint(1000, 9999),
        "username": username,
        "firstName": "Alice",
        "lastName": "Smith",
        "email": f"{username}@example.com",
        "password": "password",
        "userStatus": 1,
    }
    api.post("/user", json=payload)

    response = api.get(f"/user/{username}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=USER_SCHEMA)
    assert data["username"] == username


def test_get_user_by_name_not_found(api):
    non_existent_user = f"nonexistent_{uuid.uuid4().hex}"
    response = api.get(f"/user/{non_existent_user}")
    assert response.status_code == 404


def test_put_user_success(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": random.randint(1000, 9999),
        "username": username,
        "firstName": "InitialFirst",
        "lastName": "InitialLast",
        "email": f"{username}@example.com",
        "password": "pass",
        "userStatus": 1,
    }
    api.post("/user", json=payload)

    updated_payload = {
        "id": payload["id"],
        "username": username,
        "firstName": "UpdatedFirst",
        "lastName": "UpdatedLast",
        "email": f"updated_{username}@example.com",
        "password": "newpass",
        "userStatus": 2,
    }
    response = api.put(f"/user/{username}", json=updated_payload)
    assert response.status_code == 200


def test_put_user_not_found(api):
    non_existent = f"nonexistent_{uuid.uuid4().hex}"
    payload = {
        "id": 12345,
        "username": non_existent,
        "firstName": "No",
        "lastName": "Body",
    }
    response = api.put(f"/user/{non_existent}", json=payload)
    assert response.status_code in [400, 404]


def test_delete_user_success(api):
    username = f"user_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": random.randint(1000, 9999),
        "username": username,
        "firstName": "ToDelete",
        "lastName": "User",
        "email": f"{username}@example.com",
    }
    api.post("/user", json=payload)

    response = api.delete(f"/user/{username}")
    assert response.status_code == 200


def test_delete_user_not_found(api):
    non_existent = f"nonexistent_{uuid.uuid4().hex}"
    response = api.delete(f"/user/{non_existent}")
    assert response.status_code == 404


def test_get_user_login_success(api):
    params = {"username": "testUser", "password": "testPassword"}
    response = api.get("/user/login", params=params)
    assert response.status_code == 200
    assert isinstance(response.text, str)


def test_get_user_login_invalid(api):
    response = api.get("/user/login", params={})
    assert response.status_code in [200, 400]


def test_get_user_logout_success(api):
    response = api.get("/user/logout")
    assert response.status_code == 200
