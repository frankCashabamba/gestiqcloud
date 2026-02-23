from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TipoImpuestoIn:
    country_code: str
    code: str
    name: str
    rate_default: float | None = None
    active: bool = True


@dataclass
class TipoImpuestoOut:
    id: str
    country_code: str
    code: str
    name: str
    rate_default: float | None
    active: bool
