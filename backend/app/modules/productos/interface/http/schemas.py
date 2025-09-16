from __future__ import annotations

from pydantic import BaseModel, Field


class ProductoInSchema(BaseModel):
    nombre: str = Field(min_length=1)
    precio: float = Field(ge=0)
    activo: bool = True


class ProductoOutSchema(BaseModel):
    id: int
    nombre: str
    precio: float
    activo: bool

