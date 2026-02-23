from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TipoDocumentoIn:
    code: str
    name: str
    description: str | None = None
    active: bool = True


@dataclass
class TipoDocumentoOut:
    id: int
    code: str
    name: str
    description: str | None
    active: bool
