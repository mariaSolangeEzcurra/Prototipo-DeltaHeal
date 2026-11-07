"""API de demostración (Pet Store mínima) para probar el pipeline de punta a punta.

Ejecutar:  uvicorn examples.demo_api.app:app --port 8000
Con DEMO_REGRESSION=1, GET /pets/{petId} devuelve 500 (regresión simulada).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

app = FastAPI(title="Demo Pet Store", version="2.0.0")


class PetIn(BaseModel):
    name: str = Field(min_length=1)
    tag: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0)


class PetPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    tag: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0)


class Pet(PetIn):
    id: int


_db: dict[int, Pet] = {}
_seq = {"n": 0}


@app.get("/pets", response_model=list[Pet])
def list_pets(limit: int = Query(default=20, ge=1, le=100)):
    return list(_db.values())[:limit]


@app.post("/pets", response_model=Pet, status_code=201)
def create_pet(p: PetIn):
    _seq["n"] += 1
    pet = Pet(id=_seq["n"], **p.model_dump())
    _db[pet.id] = pet
    return pet


@app.get("/pets/{petId}", response_model=Pet)
def get_pet(petId: int):
    if os.getenv("DEMO_REGRESSION") == "1":
        raise HTTPException(500, "regresión simulada")
    if petId not in _db:
        raise HTTPException(404, "Pet not found")
    return _db[petId]


@app.patch("/pets/{petId}", response_model=Pet)
def patch_pet(petId: int, p: PetPatch):
    if petId not in _db:
        raise HTTPException(404, "Pet not found")
    cur = _db[petId].model_dump()
    cur.update({k: v for k, v in p.model_dump().items() if v is not None})
    _db[petId] = Pet(**cur)
    return _db[petId]


@app.delete("/pets/{petId}", status_code=204)
def delete_pet(petId: int):
    if petId not in _db:
        raise HTTPException(404, "Pet not found")
    del _db[petId]
    return Response(status_code=204)
