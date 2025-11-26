from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HorarioAtencionIn:
    weekday_id: int
    start_time: str
    end_time: str


@dataclass
class HorarioAtencionOut:
    id: int
    weekday_id: int
    start_time: str
    end_time: str
