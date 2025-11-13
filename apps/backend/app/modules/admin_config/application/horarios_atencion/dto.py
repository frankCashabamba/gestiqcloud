from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HorarioAtencionIn:
    dia_id: int
    inicio: str
    fin: str


@dataclass
class HorarioAtencionOut:
    id: int
    dia_id: int
    inicio: str
    fin: str
