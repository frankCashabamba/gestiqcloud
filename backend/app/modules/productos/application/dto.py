from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProductoIn:
    nombre: str
    precio: float
    activo: bool = True


@dataclass
class ProductoOut:
    id: int
    nombre: str
    precio: float
    activo: bool

