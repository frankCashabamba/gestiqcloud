from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TimezoneIn:
    name: str
    display_name: str
    offset_minutes: Optional[int] = None
    active: bool = True


@dataclass
class TimezoneOut:
    name: str
    display_name: str
    offset_minutes: Optional[int]
    active: bool
