from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class DiaSemanaIn:
    code: str
    name: str
    order: int


@dataclass
class DiaSemanaOut:
    id: UUID
    code: str
    name: str
    order: int
