from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TipoNegocioIn:
    name: str
    description: Optional[str] = None
    active: bool = True


@dataclass
class TipoNegocioOut:
    id: int
    name: str
    description: Optional[str]
    active: bool
