from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LocaleIn:
    code: str
    name: str
    active: bool = True


@dataclass
class LocaleOut:
    code: str
    name: str
    active: bool
