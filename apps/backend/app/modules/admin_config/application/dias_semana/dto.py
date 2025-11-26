from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiaSemanaIn:
    code: str
    name: str
    order: int


@dataclass
class DiaSemanaOut:
    id: int
    code: str
    name: str
    order: int
