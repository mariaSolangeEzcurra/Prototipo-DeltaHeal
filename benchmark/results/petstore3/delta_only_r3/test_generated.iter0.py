import random
import uuid
import pytest
from jsonschema import validate

# Schema definition for Pet according to OpenAPI component
PET_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
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


def _generate_random_pet():
    pet_id = random.randint(100000, 999999)
    tag_id = random.randint(1, 100)
    tag_name = f"tag_{uuid.uuid4().hex[:6]}"
    return {
        "id": pet_id,
        "name": f"pet_{uuid.uuid4().hex[:8]}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": [{"id": tag_id, "name": tag_name}],
        "status": "available",
    }


# ==============================================================================
# POST /pet - addPet
# ==============================================================================

def test_post_pet_success(api):
    payload = _generate_random_pet()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_invalid_input(api):
    # Missing required fields 'name' and 'photoUrls'
    invalid_payload = {"status": "available"}
    response = api.post("/pet", json=invalid_payload)
    assert response.status_code in [400, 422]


def test_post_pet_invalid_status_enum(api):
    payload = _generate_random_pet()
    payload["status"] = "not_a_valid_status"
    response = api.post("/pet", json=payload)
    assert response.status_code in [400, 422]


# ==============================================================================
# PUT /pet - updatePet
# ==============================================================================

def test_put_pet_success(api):
    initial_pet = _generate_random_pet()
    create_resp = api.post("/pet", json=initial_pet)
    assert create_resp.status_code == 200
    created_id = create_resp.json().get("id", initial_pet["id"])

    updated_payload = initial_pet.copy()
    updated_payload["id"] = created_id
    updated_payload["name"] = f"updated_{uuid.uuid4().hex[:8]}"
    updated_payload["status"] = "sold"

    response = api.put("/pet", json=updated_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == updated_payload["name"]
    assert data["status"] == "sold"


def test_put_pet_not_found(api):
    non_existent_id = random.randint(900000000, 999999999)
    payload = _generate_random_pet()
    payload["id"] = non_existent_id
    response = api.put("/pet", json=payload)
    assert response.status_code in [404, 400]


def test_put_pet_invalid_id(api):
    payload = _generate_random_pet()
    payload["id"] = "not-an-integer-id"
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 422]


def test_put_pet_validation_exception(api):
    # Missing required 'name' field
    payload = {
        "id": 1,
        "photoUrls": ["https://example.com/photo.jpg"],
    }
    response = api.put("/pet", json=payload)
    assert response.status_code in [400, 422]


# ==============================================================================
# GET /pet/{petId} - getPetById
# ==============================================================================

def test_get_pet_by_id_success(api):
    pet_data = _generate_random_pet()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id
    assert data["name"] == pet_data["name"]


def test_get_pet_by_id_not_found(api):
    non_existent_id = random.randint(900000000, 999999999)
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


def test_get_pet_by_id_invalid_id(api):
    response = api.get("/pet/invalid-string-id")
    assert response.status_code == 400


# ==============================================================================
# POST /pet/{petId} - updatePetWithForm
# ==============================================================================

def test_post_pet_update_with_form_success(api):
    pet_data = _generate_random_pet()
    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200
    pet_id = create_resp.json().get("id", pet_data["id"])

    new_name = f"renamed_{uuid.uuid4().hex[:6]}"
    new_status = "pending"

    response = api.post(f"/pet/{pet_id}?name={new_name}&status={new_status}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == new_name
    assert data["status"] == new_status


def test_post_pet_update_with_form_invalid_id(api):
    response = api.post("/pet/not-an-int?name=Spot&status=available")
    assert response.status_code == 400


# ==============================================================================
# GET /pet/findByStatus - findPetsByStatus
# ==============================================================================

@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_find_pets_by_status_success(api, status):
    response = api.get(f"/pet/findByStatus?status={status}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)
        if "status" in pet:
            assert pet["status"] == status


def test_get_find_pets_by_status_invalid_value(api):
    response = api.get("/pet/findByStatus?status=invalid_status_value")
    assert response.status_code == 400


# ==============================================================================
# GET /pet/findByTags - findPetsByTags
# ==============================================================================

def test_get_find_pets_by_tags_success(api):
    unique_tag = f"tag_{uuid.uuid4().hex[:8]}"
    pet_data = _generate_random_pet()
    pet_data["tags"] = [{"id": 1, "name": unique_tag}]

    create_resp = api.post("/pet", json=pet_data)
    assert create_resp.status_code == 200

    response = api.get(f"/pet/findByTags?tags={unique_tag}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for pet in data:
        validate(instance=pet, schema=PET_SCHEMA)
    assert any(pet.get("name") == pet_data["name"] for pet in data)


# ==============================================================================
# DELETE /store/order/{orderId} - deleteOrder
# ==============================================================================

def test_delete_order_invalid_id(api):
    response = api.delete("/store/order/non-numeric-id")
    assert response.status_code == 400


def test_delete_order_out_of_bounds_id(api):
    # IDs > 1000 generate API errors per contract description
    response = api.delete("/store/order/99999")
    assert response.status_code in [400, 404]


def test_delete_order_not_found(api):
    # Non-existent order with ID within typical range
    response = api.delete("/store/order/999")
    assert response.status_code in [200, 404]
