from __future__ import annotations

from dataclasses import dataclass


@dataclass
class IdiomaIn:
    code: str
    name: str
    active: bool = True


@dataclass
class IdiomaOut:
    id: int
    code: str
    name: str
    active: bool
