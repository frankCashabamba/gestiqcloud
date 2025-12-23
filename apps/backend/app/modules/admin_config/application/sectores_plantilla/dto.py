from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class SectorPlantillaIn:
    name: str
    code: str | None = None
    description: str | None = None
    template_config: dict = field(default_factory=dict)
    active: bool = True


@dataclass
class SectorPlantillaOut:
    id: UUID
    name: str
    code: str | None
    description: str | None
    template_config: dict
    active: bool
    created_at: datetime
    updated_at: datetime
    config_version: int | None = None
