import random
import jsonschema
import pytest

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

PET_ARRAY_SCHEMA = {
    "type": "array",
    "items": PET_SCHEMA,
}


def _generate_random_pet():
    pet_id = random.randint(100000, 999999)
    return {
        "id": pet_id,
        "name": f"pet_{pet_id}",
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": [{"id": 1, "name": f"tag_{pet_id}"}],
        "status": "available",
    }


def _create_pet_helper(api):
    pet_payload = _generate_random_pet()
    res = api.post("/pet", json=pet_payload)
    if res.status_code == 200:
        return res.json()
    return pet_payload


# ==============================================================================
# POST /pet (addPet)
# ==============================================================================


def test_post_pet_success_200(api):
    payload = _generate_random_pet()
    response = api.post("/pet", json=payload)
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_SCHEMA)
    assert body["name"] == payload["name"]


def test_post_pet_missing_required_fields_400_or_422(api):
    # Missing required 'name' and 'photoUrls'
    invalid_payload = {"status": "available"}
    response = api.post("/pet", json=invalid_payload)
    assert response.status_code in (400, 422)


def test_post_pet_invalid_status_enum_400_or_422(api):
    payload = _generate_random_pet()
    payload["status"] = "non_existent_status"
    response = api.post("/pet", json=payload)
    assert response.status_code in (400, 422)


# ==============================================================================
# PUT /pet (updatePet)
# ==============================================================================


def test_put_pet_success_200(api):
    pet = _create_pet_helper(api)
    updated_payload = dict(pet)
    updated_payload["name"] = f"updated_{pet['id']}"
    updated_payload["status"] = "sold"

    response = api.put("/pet", json=updated_payload)
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_SCHEMA)
    assert body["name"] == updated_payload["name"]
    assert body["status"] == "sold"


def test_put_pet_invalid_id_400(api):
    payload = _generate_random_pet()
    payload["id"] = "invalid_string_id"
    response = api.put("/pet", json=payload)
    assert response.status_code in (400, 422)


def test_put_pet_non_existent_404(api):
    payload = _generate_random_pet()
    payload["id"] = 999999999999
    response = api.put("/pet", json=payload)
    assert response.status_code in (404, 400)


def test_put_pet_missing_required_fields_422_or_400(api):
    response = api.put("/pet", json={"id": 123})
    assert response.status_code in (400, 422)


# ==============================================================================
# GET /pet/findByStatus (findPetsByStatus)
# ==============================================================================


@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pet_find_by_status_success_200(api, status):
    response = api.get("/pet/findByStatus", params={"status": status})
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_ARRAY_SCHEMA)
    for pet in body:
        if "status" in pet and pet["status"]:
            assert pet["status"] == status


def test_get_pet_find_by_status_invalid_status_400(api):
    response = api.get("/pet/findByStatus", params={"status": "invalid_status_xyz"})
    assert response.status_code == 400


# ==============================================================================
# GET /pet/findByTags (findPetsByTags)
# ==============================================================================


def test_get_pet_find_by_tags_success_200(api):
    pet = _create_pet_helper(api)
    tag_name = pet["tags"][0]["name"] if pet.get("tags") else "tag1"

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_ARRAY_SCHEMA)


def test_get_pet_find_by_tags_empty_400(api):
    response = api.get("/pet/findByTags", params={"tags": ""})
    assert response.status_code in (200, 400)


# ==============================================================================
# GET /pet/{petId} (getPetById)
# ==============================================================================


def test_get_pet_by_id_success_200(api):
    created_pet = _create_pet_helper(api)
    pet_id = created_pet["id"]

    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_SCHEMA)
    assert body["id"] == pet_id


def test_get_pet_by_id_invalid_id_400(api):
    response = api.get("/pet/invalid_id_format")
    assert response.status_code == 400


def test_get_pet_by_id_not_found_404(api):
    response = api.get("/pet/999999999999")
    assert response.status_code == 404


# ==============================================================================
# POST /pet/{petId} (updatePetWithForm)
# ==============================================================================


def test_post_pet_update_with_form_success_200(api):
    created_pet = _create_pet_helper(api)
    pet_id = created_pet["id"]
    new_name = f"renamed_{pet_id}"
    new_status = "sold"

    response = api.post(f"/pet/{pet_id}", params={"name": new_name, "status": new_status})
    assert response.status_code == 200
    body = response.json()
    jsonschema.validate(instance=body, schema=PET_SCHEMA)


def test_post_pet_update_with_form_invalid_input_400(api):
    response = api.post("/pet/invalid_pet_id", params={"name": "test"})
    assert response.status_code in (400, 404)


# ==============================================================================
# DELETE /store/order/{orderId} (deleteOrder)
# ==============================================================================


def test_delete_store_order_success_200(api):
    # Doc: "For valid response try integer IDs with value < 1000"
    valid_order_id = random.randint(1, 999)
    response = api.delete(f"/store/order/{valid_order_id}")
    assert response.status_code in (200, 404)


def test_delete_store_order_invalid_id_400(api):
    # Doc: "non-integers will generate API errors"
    response = api.delete("/store/order/non_integer_id")
    assert response.status_code == 400


def test_delete_store_order_not_found_404(api):
    # Doc: "Anything above 1000 or non-integers will generate API errors."
    response = api.delete("/store/order/999999")
    assert response.status_code in (404, 400)
