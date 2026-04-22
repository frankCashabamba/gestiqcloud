from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass
class HorarioAtencionIn:
    weekday_id: UUID
    start_time: str
    end_time: str


@dataclass
class HorarioAtencionOut:
    id: UUID
    weekday_id: UUID
    start_time: str
    end_time: str
