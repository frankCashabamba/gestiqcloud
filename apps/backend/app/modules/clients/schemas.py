"""Module: schemas.py

Auto-generated module docstring."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    """Class ClienteBase - auto-generated docstring."""

    name: str
    identificacion: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    localidad: Optional[str] = None
    state: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None


class ClienteCreate(ClienteBase):
    """Class ClienteCreate - auto-generated docstring."""

    pass


class ClienteUpdate(ClienteBase):
    """Class ClienteUpdate - auto-generated docstring."""

    pass


class ClienteOut(ClienteBase):
    """Class ClienteOut - auto-generated docstring."""

    id: int

    model_config = ConfigDict(from_attributes=True)
