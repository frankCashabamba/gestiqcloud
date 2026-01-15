"""Module: schemas.py

Auto-generated module docstring."""

from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    """Class ClienteBase - auto-generated docstring."""

    name: str
    identificacion: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    localidad: str | None = None
    state: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    is_wholesale: bool | None = False


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
