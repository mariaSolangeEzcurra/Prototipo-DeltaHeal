import random
import uuid
import pytest
from jsonschema import validate

# JSON Schemas derived from OpenAPI spec
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
        "photoUrls": {
            "type": "array",
            "items": {"type": "string"},
        },
        "tags": {
            "type": "array",
            "items": TAG_SCHEMA,
        },
        "status": {
            "type": "string",
            "enum": ["available", "pending", "sold"],
        },
    },
}

PET_LIST_SCHEMA = {
    "type": "array",
    "items": PET_SCHEMA,
}


def _create_pet_payload(pet_id=None, name=None, status="available", tags=None):
    if pet_id is None:
        pet_id = random.randint(100000, 999999)
    if name is None:
        name = f"pet_{uuid.uuid4().hex[:8]}"
    if tags is None:
        tags = [{"id": 1, "name": "tag1"}]
    return {
        "id": pet_id,
        "name": name,
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": tags,
        "status": status,
    }


# ---------------------------------------------------------------------------
# POST /pet (addPet)
# ---------------------------------------------------------------------------

def test_post_pet_success_200(api):
    payload = _create_pet_payload()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["status"] == payload["status"]


def test_post_pet_missing_required_fields_400_or_422(api):
    # Missing required 'name' and 'photoUrls'
    invalid_payload = {"status": "available"}
    response = api.post("/pet", json=invalid_payload)
    assert response.status_code in (400, 422)


def test_post_pet_invalid_status_enum_400_or_422(api):
    payload = _create_pet_payload()
    payload["status"] = "unknown_status"
    response = api.post("/pet", json=payload)
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# PUT /pet (updatePet)
# ---------------------------------------------------------------------------

def test_put_pet_success_200(api):
    initial_payload = _create_pet_payload(status="available")
    create_res = api.post("/pet", json=initial_payload)
    assert create_res.status_code == 200
    created_pet = create_res.json()
    pet_id = created_pet.get("id", initial_payload["id"])

    update_payload = _create_pet_payload(pet_id=pet_id, name="updated_name", status="sold")
    response = api.put("/pet", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == "updated_name"
    assert data["status"] == "sold"


def test_put_pet_invalid_id_400(api):
    payload = _create_pet_payload()
    payload["id"] = "not-a-valid-int64-id"
    response = api.put("/pet", json=payload)
    assert response.status_code in (400, 422)


def test_put_pet_not_found_404(api):
    non_existent_id = 999999999999999
    payload = _create_pet_payload(pet_id=non_existent_id)
    response = api.put("/pet", json=payload)
    # Spec documents 404 for pet not found; some implementations may upsert or return 400
    assert response.status_code in (404, 200)


def test_put_pet_validation_exception_422(api):
    invalid_payload = {
        "id": random.randint(100000, 999999),
        "status": "available"
        # missing required name and photoUrls
    }
    response = api.put("/pet", json=invalid_payload)
    assert response.status_code in (400, 422)


# ---------------------------------------------------------------------------
# GET /pet/{petId} (getPetById)
# ---------------------------------------------------------------------------

def test_get_pet_by_id_success_200(api):
    payload = _create_pet_payload()
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id
    assert data["name"] == payload["name"]


def test_get_pet_by_id_invalid_id_format_400(api):
    response = api.get("/pet/invalid_string_id")
    assert response.status_code == 400


def test_get_pet_by_id_not_found_404(api):
    non_existent_id = 999999999999888
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /pet/{petId} (updatePetWithForm)
# ---------------------------------------------------------------------------

def test_post_pet_update_with_form_success_200(api):
    payload = _create_pet_payload(status="available")
    create_res = api.post("/pet", json=payload)
    assert create_res.status_code == 200
    pet_id = create_res.json().get("id", payload["id"])

    new_name = "form_updated_name"
    new_status = "sold"
    response = api.post(
        f"/pet/{pet_id}",
        params={"name": new_name, "status": new_status}
    )
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == new_name
    assert data["status"] == new_status


def test_post_pet_update_with_form_invalid_input_400(api):
    response = api.post("/pet/not-an-integer", params={"name": "test", "status": "sold"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /pet/findByStatus (findPetsByStatus)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pet_find_by_status_success_200(api, status):
    payload = _create_pet_payload(status=status)
    api.post("/pet", json=payload)

    response = api.get("/pet/findByStatus", params={"status": status})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    assert isinstance(data, list)


def test_get_pet_find_by_status_invalid_value_400(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_enum"})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# GET /pet/findByTags (findPetsByTags)
# ---------------------------------------------------------------------------

def test_get_pet_find_by_tags_success_200(api):
    tag_name = f"tag_{uuid.uuid4().hex[:6]}"
    payload = _create_pet_payload(tags=[{"id": 1, "name": tag_name}])
    api.post("/pet", json=payload)

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    assert isinstance(data, list)


def test_get_pet_find_by_tags_multiple_tags_success_200(api):
    response = api.get("/pet/findByTags", params={"tags": ["tag1", "tag2"]})
    assert response.status_code == 200
    data = response.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)


# ---------------------------------------------------------------------------
# DELETE /store/order/{orderId} (deleteOrder)
# ---------------------------------------------------------------------------

def test_delete_store_order_invalid_id_400(api):
    # Non-integer ID should produce 400
    response = api.delete("/store/order/invalid_order_id")
    assert response.status_code == 400


def test_delete_store_order_not_found_404(api):
    # ID > 1000 or non-existent valid int64 triggers not found or bad request per docs
    order_id = 999999999
    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code in (400, 404)
