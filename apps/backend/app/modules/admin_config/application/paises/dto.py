from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class PaisIn:
    code: str
    name: str
    active: bool = True


@dataclass
class PaisOut:
    id: UUID
    code: str
    name: str
    active: bool
