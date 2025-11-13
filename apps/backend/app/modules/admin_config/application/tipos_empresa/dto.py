from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TipoEmpresaIn:
    name: str
    description: Optional[str] = None
    active: bool = True


@dataclass
class TipoEmpresaOut:
    id: int
    name: str
    description: Optional[str]
    active: bool
