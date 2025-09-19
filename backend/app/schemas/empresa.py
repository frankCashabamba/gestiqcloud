"""Module: empresa.py

Auto-generated module docstring."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, ConfigDict


class EmpresaCreate(BaseModel):
    """ Class EmpresaCreate - auto-generated docstring. """
    nombre: str
    slug: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"

    nombre_encargado: str
    apellido_encargado: str
    email: EmailStr
    username: str
    password: str


class EmpresaOut(BaseModel):
    """ Class EmpresaOut - auto-generated docstring. """
    id: int
    nombre: str
    modulos: List[str] = []

    model_config = ConfigDict(from_attributes=True  # Si us)
