from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiaSemanaIn:
    clave: str
    nombre: str
    orden: int


@dataclass
class DiaSemanaOut:
    id: int
    clave: str
    nombre: str
    orden: int
