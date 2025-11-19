from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class TipoEmpresaIn:
    name: str
    description: str | None = None
    active: bool = True


@dataclass
class TipoEmpresaOut:
    id: UUID
    name: str
    description: str | None
    active: bool
