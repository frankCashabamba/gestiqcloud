"""Unified User protocol for identity module.

Provides a structural type that both SuperUser and CompanyUser satisfy,
allowing the identity use cases to work with either user model.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class User(Protocol):
    id: UUID
    email: str
    name: str | None
    is_active: bool
    password_hash: str
