from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ClienteInSchema(BaseModel):
    name: str = Field(min_length=1)
    identificacion: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    localidad: Optional[str] = None
    state: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None


class ClienteOutSchema(BaseModel):
    id: str
    name: str
    identificacion: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    localidad: Optional[str] = None
    state: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None
