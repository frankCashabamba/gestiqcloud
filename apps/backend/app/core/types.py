"""Module: types.py

Auto-generated module docstring."""

# app/core/types.py
from typing import Protocol, runtime_checkable


@runtime_checkable
class HasID(Protocol):
    """ Class HasID - auto-generated docstring. """
    id: int


class HasEmpresaID(HasID, Protocol):
    """ Class HasEmpresaID - auto-generated docstring. """
    empresa_id: int