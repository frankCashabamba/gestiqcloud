from __future__ import annotations

from pydantic import BaseModel, Field


class ClienteInSchema(BaseModel):
    name: str = Field(min_length=1)
    identificacion: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    localidad: str | None = None
    state: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None


class ClienteOutSchema(BaseModel):
    id: str
    name: str
    identificacion: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    localidad: str | None = None
    state: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
