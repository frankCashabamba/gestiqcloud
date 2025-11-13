from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TipoEmpresaIn:
    name: str
    description: str | None = None
    active: bool = True


@dataclass
class TipoEmpresaOut:
    id: int
    name: str
    description: str | None
    active: bool
