from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UnidadMedidaIn:
    code: str
    name: str
    abbreviation: str
    active: bool = True


@dataclass
class UnidadMedidaOut:
    id: int
    code: str
    name: str
    abbreviation: str
    active: bool
