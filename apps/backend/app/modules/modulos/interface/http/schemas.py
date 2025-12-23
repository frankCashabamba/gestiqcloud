from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ModuloOutSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    url: str | None = None
    icon: str | None = None
    category: str | None = None
    description: str | None = None
    initial_template: str | None = None
    context_type: str | None = None
    target_model: str | None = None
    context_filters: dict | None = None
    active: bool
