import pytest
import requests
import json
import uuid
import random
import string
from jsonschema import validate, ValidationError

# --- Schemas for validation (simplified for required fields and types) ---

pet_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "category": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"}
            },
            "required": ["id", "name"] # Assuming category always has id and name if present
        },
        "photoUrls": {
            "type": "array",
            "items": {"type": "string"}
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                },
                "required": ["id", "name"] # Assuming tag always has id and name if present
            }
        },
        "status": {"type": "string", "enum": ["available", "pending", "sold"]}
    },
    "required": ["name", "photoUrls"]
}

pet_array_schema = {
    "type": "array",
    "items": pet_schema
}

# --- Helper functions ---

def generate_random_pet_data(pet_id=None, status=None):
    """Generates a valid Pet object payload."""
    name = f"doggie-{uuid.uuid4().hex[:8]}"
    photo_urls = [f"http://example.com/photo/{uuid.uuid4().hex[:8]}.jpg"]
    category = {"id": random.randint(1, 100), "name": random.choice(["Dogs", "Cats", "Birds"])}
    tags = [{"id": random.randint(1, 100), "name": f"tag-{random.choice(string.ascii_lowercase)}"} for _ in range(random.randint(1, 3))]
    
    pet_data = {
        "name": name,
        "photoUrls": photo_urls,
        "category": category,
        "tags": tags,
        "status": status if status else random.choice(["available", "pending", "sold"])
    }
    if pet_id is not None:
        pet_data["id"] = pet_id
    return pet_data

def create_pet(api, pet_data=None):
    """Helper to create a pet and return its ID and the full object."""
    if pet_data is None:
        pet_data = generate_random_pet_data()
    
    response = api.post("/pet", json=pet_data)
    assert response.status_code == 200
    created_pet = response.json()
    validate(instance=created_pet, schema=pet_schema)
    assert "id" in created_pet
    return created_pet["id"], created_pet

# --- Tests for /pet (POST) ---

def test_post_pet_success(api):
    """Test adding a new pet with valid data."""
    pet_data = generate_random_pet_data()
    response = api.post("/pet", json=pet_data)
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_schema)
    assert response_json["name"] == pet_data["name"]
    assert response_json["photoUrls"] == pet_data["photoUrls"]
    assert "id" in response_json

def test_post_pet_invalid_input_missing_name(api):
    """Test adding a pet with missing required 'name' field."""
    pet_data = generate_random_pet_data()
    del pet_data["name"]
    response = api.post("/pet", json=pet_data)
    # OpenAPI spec indicates 400 for Invalid input or 422 for Validation exception
    assert response.status_code in [400, 422]

def test_post_pet_invalid_input_missing_photoUrls(api):
    """Test adding a pet with missing required 'photoUrls' field."""
    pet_data = generate_random_pet_data()
    del pet_data["photoUrls"]
    response = api.post("/pet", json=pet_data)
    assert response.status_code in [400, 422]

def test_post_pet_invalid_status_value(api):
    """Test adding a pet with an invalid status value."""
    pet_data = generate_random_pet_data()
    pet_data["status"] = "invalid_status"
    response = api.post("/pet", json=pet_data)
    assert response.status_code in [400, 422] # Expecting validation error

# --- Tests for /pet (PUT) ---

def test_put_pet_success(api):
    """Test updating an existing pet with valid data."""
    pet_id, original_pet = create_pet(api)
    updated_name = f"updated-doggie-{uuid.uuid4().hex[:8]}"
    updated_status = "sold"
    
    updated_pet_data = original_pet.copy()
    updated_pet_data["name"] = updated_name
    updated_pet_data["status"] = updated_status
    
    response = api.put("/pet", json=updated_pet_data)
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_schema)
    assert response_json["id"] == pet_id
    assert response_json["name"] == updated_name
    assert response_json["status"] == updated_status

def test_put_pet_invalid_id_supplied(api):
    """Test updating a pet with an invalid (non-existent) ID."""
    non_existent_id = 999999999999999999 # A very large ID unlikely to exist
    pet_data = generate_random_pet_data(pet_id=non_existent_id)
    response = api.put("/pet", json=pet_data)
    assert response.status_code == 400 # Invalid ID supplied

def test_put_pet_not_found(api):
    """Test updating a pet that does not exist."""
    non_existent_id = 999999999999999998 # Another non-existent ID
    pet_data = generate_random_pet_data(pet_id=non_existent_id)
    response = api.put("/pet", json=pet_data)
    assert response.status_code == 404 # Pet not found

def test_put_pet_validation_exception_invalid_status(api):
    """Test updating a pet with an invalid status value."""
    pet_id, original_pet = create_pet(api)
    updated_pet_data = original_pet.copy()
    updated_pet_data["status"] = "invalid_status_value"
    response = api.put("/pet", json=updated_pet_data)
    assert response.status_code == 422 # Validation exception

# --- Tests for /pet/findByStatus (GET) ---

def test_get_pet_findByStatus_success_available(api):
    """Test finding pets by 'available' status."""
    # Create a pet with 'available' status
    pet_id, _ = create_pet(api, generate_random_pet_data(status="available"))
    
    response = api.get("/pet/findByStatus", params={"status": "available"})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_array_schema)
    assert any(pet["id"] == pet_id for pet in response_json)
    assert all(pet["status"] == "available" for pet in response_json if "status" in pet)

def test_get_pet_findByStatus_success_multiple_status(api):
    """Test finding pets by multiple status values."""
    # Create pets with 'pending' and 'sold' status
    pet_id_pending, _ = create_pet(api, generate_random_pet_data(status="pending"))
    pet_id_sold, _ = create_pet(api, generate_random_pet_data(status="sold"))

    response = api.get("/pet/findByStatus", params={"status": "pending,sold"})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_array_schema)
    assert any(pet["id"] == pet_id_pending for pet in response_json)
    assert any(pet["id"] == pet_id_sold for pet in response_json)
    assert all(pet["status"] in ["pending", "sold"] for pet in response_json if "status" in pet)

def test_get_pet_findByStatus_invalid_status_value(api):
    """Test finding pets with an invalid status query parameter."""
    response = api.get("/pet/findByStatus", params={"status": "invalid_status"})
    assert response.status_code == 400 # Invalid status value

def test_get_pet_findByStatus_no_status_param(api):
    """Test finding pets without providing a status parameter (should use default 'available')."""
    # Create an 'available' pet to ensure results
    pet_id, _ = create_pet(api, generate_random_pet_data(status="available"))

    response = api.get("/pet/findByStatus") # No params, should default to 'available'
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_array_schema)
    assert any(pet["id"] == pet_id for pet in response_json)
    assert all(pet["status"] == "available" for pet in response_json if "status" in pet)

# --- Tests for /pet/findByTags (GET) ---

def test_get_pet_findByTags_success_single_tag(api):
    """Test finding pets by a single tag."""
    tag_name = f"test-tag-{uuid.uuid4().hex[:4]}"
    pet_data = generate_random_pet_data()
    pet_data["tags"] = [{"id": 1, "name": tag_name}]
    pet_id, _ = create_pet(api, pet_data)

    response = api.get("/pet/findByTags", params={"tags": tag_name})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_array_schema)
    assert any(pet["id"] == pet_id for pet in response_json)
    assert all(any(t["name"] == tag_name for t in pet.get("tags", [])) for pet in response_json)

def test_get_pet_findByTags_success_multiple_tags(api):
    """Test finding pets by multiple tags."""
    tag1 = f"tagA-{uuid.uuid4().hex[:4]}"
    tag2 = f"tagB-{uuid.uuid4().hex[:4]}"
    pet_data = generate_random_pet_data()
    pet_data["tags"] = [{"id": 1, "name": tag1}, {"id": 2, "name": tag2}]
    pet_id, _ = create_pet(api, pet_data)

    response = api.get("/pet/findByTags", params={"tags": f"{tag1},{tag2}"})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_array_schema)
    assert any(pet["id"] == pet_id for pet in response_json)
    assert all(any(t["name"] in [tag1, tag2] for t in pet.get("tags", [])) for pet in response_json)

def test_get_pet_findByTags_invalid_tag_value(api):
    """Test finding pets with an invalid tag query parameter (e.g., empty)."""
    response = api.get("/pet/findByTags", params={"tags": ""})
    # The spec indicates 400 for 'Invalid tag value'. An empty tag might be considered invalid.
    # However, some implementations might return 200 with an empty list.
    # We'll check for 400 as per spec, but be aware of potential variations.
    assert response.status_code == 400 

def test_get_pet_findByTags_no_matching_tags(api):
    """Test finding pets with tags that don't match any existing pets."""
    non_existent_tag = f"non-existent-tag-{uuid.uuid4().hex}"
    response = api.get("/pet/findByTags", params={"tags": non_existent_tag})
    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 0

# --- Tests for /pet/{petId} (GET) ---

def test_get_pet_by_id_success(api):
    """Test retrieving an existing pet by its ID."""
    pet_id, created_pet = create_pet(api)
    response = api.get(f"/pet/{pet_id}")
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_schema)
    assert response_json["id"] == pet_id
    assert response_json["name"] == created_pet["name"]

def test_get_pet_by_id_invalid_id_supplied(api):
    """Test retrieving a pet with an invalid ID format (e.g., non-integer)."""
    invalid_id = "abc"
    response = api.get(f"/pet/{invalid_id}")
    assert response.status_code == 400 # Invalid ID supplied

def test_get_pet_by_id_not_found(api):
    """Test retrieving a pet that does not exist."""
    non_existent_id = 999999999999999997 # A very large ID unlikely to exist
    response = api.get(f"/pet/{non_existent_id}")
    assert response.status_code == 404 # Pet not found

# --- Tests for /pet/{petId} (POST) ---

def test_post_pet_id_update_with_form_success(api):
    """Test updating a pet's name and status using form data."""
    pet_id, _ = create_pet(api)
    new_name = f"form-updated-name-{uuid.uuid4().hex[:8]}"
    new_status = "pending"
    
    response = api.post(f"/pet/{pet_id}", params={"name": new_name, "status": new_status})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_schema)
    assert response_json["id"] == pet_id
    assert response_json["name"] == new_name
    assert response_json["status"] == new_status

def test_post_pet_id_update_with_form_only_name(api):
    """Test updating only the pet's name using form data."""
    pet_id, original_pet = create_pet(api)
    new_name = f"form-name-only-{uuid.uuid4().hex[:8]}"
    
    response = api.post(f"/pet/{pet_id}", params={"name": new_name})
    assert response.status_code == 200
    response_json = response.json()
    validate(instance=response_json, schema=pet_schema)
    assert response_json["id"] == pet_id
    assert response_json["name"] == new_name
    # Status should remain the same as original if not provided
    assert response_json["status"] == original_pet["status"] 

def test_post_pet_id_update_with_form_invalid_id(api):
    """Test updating a pet with an invalid (non-existent) ID using form data."""
    non_existent_id = 999999999999999996
    new_name = "invalid-id-test"
    response = api.post(f"/pet/{non_existent_id}", params={"name": new_name})
    assert response.status_code == 400 # Invalid input (or 404 if pet not found, but spec says 400)

def test_post_pet_id_update_with_form_invalid_status_value(api):
    """Test updating a pet with an invalid status value using form data."""
    pet_id, _ = create_pet(api)
    invalid_status = "unknown_status"
    response = api.post(f"/pet/{pet_id}", params={"status": invalid_status})
    assert response.status_code == 400 # Invalid input (for status validation)

# --- Tests for /store/order/{orderId} (DELETE) ---

# Note: The spec does not provide a way to CREATE an order, only delete.
# For independent tests, we'll assume a valid orderId < 1000 can be used for success,
# and > 1000 for not found, as per the description.

def test_delete_order_success(api):
    """Test deleting an order with a valid ID (< 1000)."""
    # Assuming order ID 1 is valid and can be deleted.
    # In a real scenario, we'd create an order first.
    order_id = random.randint(1, 999) 
    response = api.delete(f"/store/order/{order_id}")
    assert response.status_code == 200 # order deleted

def test_delete_order_invalid_id_supplied(api):
    """Test deleting an order with an invalid ID format (e.g., non-integer)."""
    invalid_order_id = "abc"
    response = api.delete(f"/store/order/{invalid_order_id}")
    assert response.status_code == 400 # Invalid ID supplied

def test_delete_order_not_found(api):
    """Test deleting an order that does not exist (ID >= 1000)."""
    non_existent_order_id = random.randint(1000, 2000) # As per spec description
    response = api.delete(f"/store/order/{non_existent_order_id}")
    assert response.status_code == 404 # Order not found
