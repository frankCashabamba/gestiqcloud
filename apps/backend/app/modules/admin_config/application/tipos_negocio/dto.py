from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TipoNegocioIn:
    name: str
    description: str | None = None
    active: bool = True


@dataclass
class TipoNegocioOut:
    id: UUID
    name: str
    description: str | None
    active: bool
