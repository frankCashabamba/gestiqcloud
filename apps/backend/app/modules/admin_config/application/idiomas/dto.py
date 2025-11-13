from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IdiomaIn:
    codigo: str
    nombre: str
    active: bool = True


@dataclass
class IdiomaOut:
    id: int
    codigo: str
    nombre: str
    active: bool
