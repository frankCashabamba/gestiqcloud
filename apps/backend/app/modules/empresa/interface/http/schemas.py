from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class EmpresaInSchema(BaseModel):
    name: str = Field(min_length=1)
    slug: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    cp: str | None = None
    pais: str | None = None
    logo: str | None = None
    color_primario: str | None = "#4f46e5"
    active: bool | None = True
    motivo_desactivacion: str | None = None
    plantilla_inicio: str | None = "cliente"
    sitio_web: str | None = None
    config_json: dict | None = None


class EmpresaOutSchema(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    modulos: list[str] = []
