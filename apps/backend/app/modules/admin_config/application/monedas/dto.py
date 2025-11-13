from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MonedaIn:
    code: str
    name: str
    symbol: str
    active: bool = True


@dataclass
class MonedaOut:
    id: int
    code: str
    name: str
    symbol: str
    active: bool
