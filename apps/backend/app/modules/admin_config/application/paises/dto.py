from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaisIn:
    code: str
    name: str
    active: bool = True


@dataclass
class PaisOut:
    id: int
    code: str
    name: str
    active: bool
