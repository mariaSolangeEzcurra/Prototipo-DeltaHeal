import random
import uuid
import pytest
from jsonschema import validate

# ---------------------------------------------------------------------------
# Schemas JSON Schema según componentes del contrato OpenAPI
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _random_id():
    return random.randint(1_000_000, 99_999_999)


def _build_pet_payload(pet_id=None, name=None, status="available", tags=None):
    if pet_id is None:
        pet_id = _random_id()
    if name is None:
        name = f"pet_{uuid.uuid4().hex[:8]}"
    if tags is None:
        tags = [{"id": _random_id(), "name": f"tag_{uuid.uuid4().hex[:6]}"}]

    return {
        "id": pet_id,
        "name": name,
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": ["https://example.com/photo1.jpg"],
        "tags": tags,
        "status": status,
    }


def _create_pet(api, payload=None):
    if payload is None:
        payload = _build_pet_payload()
    resp = api.post("/pet", json=payload)
    assert resp.status_code == 200, f"Error creando pet previa: {resp.text}"
    return resp.json()


# ===========================================================================
# POST /pet (addPet)
# ===========================================================================
def test_post_pet_success(api):
    payload = _build_pet_payload()
    resp = api.post("/pet", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["photoUrls"] == payload["photoUrls"]


def test_post_pet_invalid_input_missing_required_fields(api):
    # 'name' y 'photoUrls' son obligatorios según el esquema
    resp = api.post("/pet", json={"status": "available"})
    assert resp.status_code in (400, 422)


def test_post_pet_invalid_input_wrong_type(api):
    # photoUrls debe ser una lista de cadenas
    resp = api.post("/pet", json={"name": "Doggo", "photoUrls": "not-a-list"})
    assert resp.status_code in (400, 422)


# ===========================================================================
# PUT /pet (updatePet)
# ===========================================================================
def test_put_pet_success(api):
    created = _create_pet(api)
    updated_payload = {
        **created,
        "name": f"updated_{uuid.uuid4().hex[:6]}",
        "status": "sold",
    }

    resp = api.put("/pet", json=updated_payload)
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == updated_payload["name"]
    assert data["status"] == "sold"


def test_put_pet_not_found(api):
    # ID que no existe
    non_existent = _build_pet_payload(pet_id=999_999_999)
    resp = api.put("/pet", json=non_existent)
    assert resp.status_code in (404, 400)


def test_put_pet_invalid_id(api):
    # ID con formato incorrecto
    payload = _build_pet_payload()
    payload["id"] = "invalid_id_format"
    resp = api.put("/pet", json=payload)
    assert resp.status_code in (400, 422)


def test_put_pet_validation_exception_missing_required(api):
    # Enviar objeto sin campos obligatorios
    resp = api.put("/pet", json={"id": _random_id()})
    assert resp.status_code in (400, 422)


# ===========================================================================
# GET /pet/{petId} (getPetById)
# ===========================================================================
def test_get_pet_by_id_success(api):
    created = _create_pet(api)
    pet_id = created["id"]

    resp = api.get(f"/pet/{petId}")
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id


def test_get_pet_by_id_not_found(api):
    resp = api.get("/pet/99999999999")
    assert resp.status_code == 404


def test_get_pet_by_id_invalid_id(api):
    resp = api.get("/pet/abc-not-an-int")
    assert resp.status_code == 400


# ===========================================================================
# POST /pet/{petId} (updatePetWithForm)
# ===========================================================================
def test_post_pet_by_id_update_with_form_success(api):
    created = _create_pet(api)
    pet_id = created["id"]
    new_name = f"renamed_{uuid.uuid4().hex[:6]}"

    resp = api.post(f"/pet/{petId}", params={"name": new_name, "status": "pending"})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == new_name
    assert data["status"] == "pending"


def test_post_pet_by_id_update_with_form_invalid_input(api):
    # petId no numérico
    resp = api.post("/pet/invalid-id", params={"name": "test"})
    assert resp.status_code in (400, 404, 422)


# ===========================================================================
# GET /pet/findByStatus (findPetsByStatus)
# ===========================================================================
@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pets_by_status_valid(api, status):
    # Aseguramos al menos una pet con ese estado
    _create_pet(api, _build_pet_payload(status=status))

    resp = api.get("/pet/findByStatus", params={"status": status})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    for pet in data:
        assert pet.get("status") == status


def test_get_pets_by_status_invalid(api):
    resp = api.get("/pet/findByStatus", params={"status": "status_que_no_existe"})
    assert resp.status_code == 400


# ===========================================================================
# GET /pet/findByTags (findPetsByTags)
# ===========================================================================
def test_get_pets_by_tags_success(api):
    unique_tag = f"tag_{uuid.uuid4().hex[:8]}"
    _create_pet(api, _build_pet_payload(tags=[{"id": 1, "name": unique_tag}]))

    resp = api.get("/pet/findByTags", params={"tags": unique_tag})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    assert len(data) >= 1
    # Verifica que la pet con el tag esté en el resultado
    matching = [
        pet
        for pet in data
        if any(t.get("name") == unique_tag for t in pet.get("tags", []))
    ]
    assert len(matching) >= 1


def test_get_pets_by_tags_invalid_empty(api):
    resp = api.get("/pet/findByTags", params={"tags": ""})
    assert resp.status_code in (200, 400)


# ===========================================================================
# DELETE /store/order/{orderId} (deleteOrder)
# ===========================================================================
def test_delete_order_success(api):
    # Según la descripción: valid response para enteros < 1000
    valid_order_id = random.randint(1, 999)
    resp = api.delete(f"/store/order/{valid_order_id}")
    # Dependiendo del estado del mock/backend puede responder 200 o 404 si no fue creada
    assert resp.status_code in (200, 404)


def test_delete_order_invalid_id_string(api):
    # Non-integers generan 400
    resp = api.delete("/store/order/not-a-number")
    assert resp.status_code == 400


def test_delete_order_invalid_id_above_limit(api):
    # La especificación indica: anything above 1000 will generate API errors (400 o 404)
    resp = api.delete("/store/order/5000")
    assert resp.status_code in (400, 404)
