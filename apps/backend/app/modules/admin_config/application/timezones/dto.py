from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TimezoneIn:
    name: str
    display_name: str
    offset_minutes: int | None = None
    active: bool = True


@dataclass
class TimezoneOut:
    name: str
    display_name: str
    offset_minutes: int | None
    active: bool
