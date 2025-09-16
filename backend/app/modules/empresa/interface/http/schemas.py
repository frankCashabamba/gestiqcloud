from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class EmpresaInSchema(BaseModel):
    nombre: str = Field(min_length=1)
    slug: Optional[str] = None
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    cp: Optional[str] = None
    pais: Optional[str] = None
    logo: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"
    activo: Optional[bool] = True
    motivo_desactivacion: Optional[str] = None
    plantilla_inicio: Optional[str] = "cliente"
    sitio_web: Optional[str] = None
    config_json: Optional[dict] = None


class EmpresaOutSchema(BaseModel):
    id: int
    nombre: str
    slug: Optional[str] = None
    modulos: list[str] = []
