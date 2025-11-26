from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModuloOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str  # English (modern)
    url: str | None = None
    icono: str | None = None
    categoria: str | None = None
    active: bool  # English (modern)
