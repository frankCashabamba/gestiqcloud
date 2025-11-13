from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, Union
from uuid import UUID


class EmpresaInSchema(BaseModel):
    name: str = Field(min_length=1)
    slug: Optional[str] = None
    tax_id: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    cp: Optional[str] = None
    pais: Optional[str] = None
    logo: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"
    active: Optional[bool] = True
    motivo_desactivacion: Optional[str] = None
    plantilla_inicio: Optional[str] = "cliente"
    sitio_web: Optional[str] = None
    config_json: Optional[dict] = None


class EmpresaOutSchema(BaseModel):
    id: Union[int, UUID]
    name: str
    slug: Optional[str] = None
    modulos: list[str] = []
