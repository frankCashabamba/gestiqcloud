from __future__ import annotations

from pydantic import BaseModel, Field


class ProductoInSchema(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(ge=0)
    active: bool = True


class ProductoOutSchema(BaseModel):
    id: int
    name: str
    price: float
    active: bool
