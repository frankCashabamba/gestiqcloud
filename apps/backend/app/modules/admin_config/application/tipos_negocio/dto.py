from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TipoNegocioIn:
    name: str
    description: str | None = None
    active: bool = True


@dataclass
class TipoNegocioOut:
    id: int
    name: str
    description: str | None
    active: bool
