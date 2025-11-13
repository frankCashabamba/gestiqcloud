"""Module: types.py

Auto-generated module docstring."""

"""Common typing protocols and aliases for IDs.

Relaxed to support both integer and UUID identifiers during the
transition to full UUID multi-tenant.
"""

# app/core/types.py
from typing import Protocol, runtime_checkable, Union
from uuid import UUID

# Accept both int and UUID (and string UUID in some SQLite contexts)
IDType = Union[int, UUID, str]


@runtime_checkable
class HasID(Protocol):
    """Class HasID - auto-generated docstring."""

    id: IDType


class HasEmpresaID(HasID, Protocol):
    """Class HasEmpresaID - auto-generated docstring."""

    tenant_id: IDType
