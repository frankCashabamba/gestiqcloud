from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ClienteInSchema(BaseModel):
    nombre: str = Field(min_length=1)
    identificacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None


class ClienteOutSchema(BaseModel):
    id: int
    nombre: str
    identificacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None

