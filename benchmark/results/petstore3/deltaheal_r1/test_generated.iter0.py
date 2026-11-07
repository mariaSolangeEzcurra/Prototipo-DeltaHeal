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


def _generar_pet_valido(pet_id=None, name=None, status="available", tag_name=None):
    """Genera el payload de una mascota válida con datos únicos."""
    if pet_id is None:
        pet_id = random.randint(100000, 999999)
    if name is None:
        name = f"pet_{uuid.uuid4().hex[:8]}"
    if tag_name is None:
        tag_name = f"tag_{uuid.uuid4().hex[:6]}"

    return {
        "id": pet_id,
        "name": name,
        "category": {"id": 1, "name": "Dogs"},
        "photoUrls": [f"https://example.com/photos/{name}.jpg"],
        "tags": [{"id": 1, "name": tag_name}],
        "status": status,
    }


# ===========================================================================
# POST /pet - addPet
# ===========================================================================
def test_post_pet_creacion_exitosa_200(api):
    payload = _generar_pet_valido()
    resp = api.post("/pet", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == payload["name"]
    assert data["photoUrls"] == payload["photoUrls"]


def test_post_pet_payload_invalido_400_o_422(api):
    # 'name' y 'photoUrls' son obligatorios según el schema
    payload_invalido = {"category": {"id": 1, "name": "Cats"}}
    resp = api.post("/pet", json=payload_invalido)
    assert resp.status_code in [400, 422]


def test_post_pet_tipo_dato_incorrecto_400_o_422(api):
    # photoUrls debe ser un array, no un string
    payload = _generar_pet_valido()
    payload["photoUrls"] = "https://invalid-url-format.com"
    resp = api.post("/pet", json=payload)
    assert resp.status_code in [400, 422]


# ===========================================================================
# PUT /pet - updatePet
# ===========================================================================
def test_put_pet_actualizacion_exitosa_200(api):
    # Paso 1: Crear la mascota
    payload = _generar_pet_valido()
    crear_resp = api.post("/pet", json=payload)
    assert crear_resp.status_code == 200
    pet_creado = crear_resp.json()
    pet_id = pet_creado.get("id", payload["id"])

    # Paso 2: Actualizar la mascota
    nuevo_nombre = f"updated_{uuid.uuid4().hex[:6]}"
    payload["id"] = pet_id
    payload["name"] = nuevo_nombre
    payload["status"] = "sold"

    update_resp = api.put("/pet", json=payload)
    assert update_resp.status_code == 200
    data = update_resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == nuevo_nombre
    assert data["status"] == "sold"


def test_put_pet_id_inexistente_404(api):
    id_inexistente = 99999999999999
    payload = _generar_pet_valido(pet_id=id_inexistente)
    resp = api.put("/pet", json=payload)
    assert resp.status_code in [404, 400]


def test_put_pet_id_invalido_400(api):
    payload = _generar_pet_valido()
    payload["id"] = "id_no_numerico_invalido"
    resp = api.put("/pet", json=payload)
    assert resp.status_code in [400, 422]


def test_put_pet_validacion_campos_requeridos_422_o_400(api):
    # Enviamos payload sin los campos requeridos (name, photoUrls)
    resp = api.put("/pet", json={"id": 12345})
    assert resp.status_code in [400, 422]


# ===========================================================================
# GET /pet/{petId} - getPetById
# ===========================================================================
def test_get_pet_por_id_exitoso_200(api):
    # Precondición: Crear la mascota
    payload = _generar_pet_valido()
    crear_resp = api.post("/pet", json=payload)
    assert crear_resp.status_code == 200
    pet_id = crear_resp.json().get("id", payload["id"])

    # Consulta por ID
    resp = api.get(f"/pet/{pet_id}")
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["id"] == pet_id
    assert data["name"] == payload["name"]


def test_get_pet_por_id_no_encontrado_404(api):
    id_inexistente = 88888888888888
    resp = api.get(f"/pet/{id_inexistente}")
    assert resp.status_code == 404


def test_get_pet_por_id_invalido_400(api):
    # petId espera un int64
    resp = api.get("/pet/abc_no_es_un_entero")
    assert resp.status_code == 400


# ===========================================================================
# POST /pet/{petId} - updatePetWithForm
# ===========================================================================
def test_post_pet_actualizar_con_form_exitoso_200(api):
    # Precondición: Crear la mascota
    payload = _generar_pet_valido()
    crear_resp = api.post("/pet", json=payload)
    assert crear_resp.status_code == 200
    pet_id = crear_resp.json().get("id", payload["id"])

    # Actualizar mediante parámetros de consulta / form data
    nombre_modificado = f"form_{uuid.uuid4().hex[:6]}"
    params = {"name": nombre_modificado, "status": "pending"}

    resp = api.post(f"/pet/{pet_id}", params=params)
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_SCHEMA)
    assert data["name"] == nombre_modificado
    assert data["status"] == "pending"


def test_post_pet_actualizar_con_form_id_invalido_400(api):
    resp = api.post("/pet/form_invalido_id", params={"name": "test"})
    assert resp.status_code in [400, 404, 422]


# ===========================================================================
# GET /pet/findByStatus - findPetsByStatus
# ===========================================================================
@pytest.mark.parametrize("status", ["available", "pending", "sold"])
def test_get_pet_find_by_status_exitoso_200(api, status):
    resp = api.get("/pet/findByStatus", params={"status": status})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    # Si la lista contiene elementos, verificar que respeten el status filtrado
    for pet in data:
        if "status" in pet:
            assert pet["status"] == status


def test_get_pet_find_by_status_invalido_400(api):
    resp = api.get("/pet/findByStatus", params={"status": "estado_inexistente_xyz"})
    assert resp.status_code == 400


# ===========================================================================
# GET /pet/findByTags - findPetsByTags
# ===========================================================================
def test_get_pet_find_by_tags_exitoso_200(api):
    tag_unico = f"tag_{uuid.uuid4().hex[:8]}"
    # Precondición: Crear una mascota con este tag específico
    payload = _generar_pet_valido(tag_name=tag_unico)
    crear_resp = api.post("/pet", json=payload)
    assert crear_resp.status_code == 200

    resp = api.get("/pet/findByTags", params={"tags": tag_unico})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)
    # Validar que al menos la mascota creada esté presente
    encontrado = any(
        any(t.get("name") == tag_unico for t in pet.get("tags", []))
        for pet in data
    )
    assert encontrado, f"No se encontró la mascota con el tag {tag_unico}"


def test_get_pet_find_by_tags_multiples_200(api):
    resp = api.get("/pet/findByTags", params={"tags": "tag1,tag2"})
    assert resp.status_code == 200
    data = resp.json()
    validate(instance=data, schema=PET_LIST_SCHEMA)


def test_get_pet_find_by_tags_invalido_400(api):
    # Parámetro vacío o con formato erróneo
    resp = api.get("/pet/findByTags", params={"tags": ""})
    assert resp.status_code in [200, 400]


# ===========================================================================
# DELETE /store/order/{orderId} - deleteOrder
# ===========================================================================
def test_delete_store_order_por_id_valido_200_o_404(api):
    # La descripción documenta: IDs enteros < 1000 son válidos
    order_id = random.randint(1, 999)
    resp = api.delete(f"/store/order/{order_id}")
    # Si la orden no existía previamente devuelve 404, de lo contrario 200
    assert resp.status_code in [200, 404]


def test_delete_store_order_id_invalido_string_400(api):
    # No entero genera 400
    resp = api.delete("/store/order/orden_invalida_no_numerica")
    assert resp.status_code == 400


def test_delete_store_order_id_fuera_de_rango_400_o_404(api):
    # IDs > 1000 según la descripción deben generar errores de API
    order_id_fuera_rango = 50000
    resp = api.delete(f"/store/order/{order_id_fuera_rango}")
    assert resp.status_code in [400, 404]
