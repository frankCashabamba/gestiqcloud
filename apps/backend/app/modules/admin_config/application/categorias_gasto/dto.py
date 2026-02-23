from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CategoriaGastoIn:
    code: str
    name: str
    parent_code: str | None = None
    active: bool = True


@dataclass
class CategoriaGastoOut:
    id: int
    code: str
    name: str
    parent_code: str | None
    active: bool
