"""Module: schemas.py

Auto-generated module docstring."""

from typing import Optional

from pydantic import BaseModel


class ClienteBase(BaseModel):
    """ Class ClienteBase - auto-generated docstring. """
    nombre: str
    identificacion: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    localidad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    codigo_postal: Optional[str] = None

class ClienteCreate(ClienteBase):
    """ Class ClienteCreate - auto-generated docstring. """
    pass

class ClienteUpdate(ClienteBase):
    """ Class ClienteUpdate - auto-generated docstring. """
    pass

class ClienteOut(ClienteBase):
    """ Class ClienteOut - auto-generated docstring. """
    id: int

    class Config:
        """ Class Config - auto-generated docstring. """
        from_attributes = True
