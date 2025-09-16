from __future__ import annotations

from pydantic import BaseModel


class ModuloOutSchema(BaseModel):
    id: int
    nombre: str
    url: str | None = None
    icono: str | None = None
    categoria: str | None = None
    activo: bool

