from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class IdiomaIn:
    code: str
    name: str
    active: bool = True


@dataclass
class IdiomaOut:
    id: UUID
    code: str
    name: str
    active: bool
