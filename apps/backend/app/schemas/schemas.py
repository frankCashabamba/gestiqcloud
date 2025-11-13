"""Module: schemas.py

Auto-generated module docstring."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr


class UsuarioCreate(BaseModel):
    """Class UsuarioCreate - auto-generated docstring."""

    nombre_encargado: str
    apellido_encargado: str
    email: EmailStr
    username: str
    password: str


class EmpresaCreate(BaseModel):
    """Class EmpresaCreate - auto-generated docstring."""

    name: str
    slug: Optional[str]
    tipo_empresa_id: Optional[int]
    tipo_negocio_id: Optional[int]
    tax_id: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    cp: Optional[str]
    pais: Optional[str]
    logo: Optional[str]
    color_primario: Optional[str] = "#4f46e5"
    plantilla_inicio: Optional[str] = "cliente"
    sitio_web: Optional[str]
    config_json: Optional[dict]
    modulos: Optional[List[int]] = []


class EmpresaConUsuarioCreate(BaseModel):
    """Class EmpresaConUsuarioCreate - auto-generated docstring."""

    empresa: EmpresaCreate
    usuario: UsuarioCreate
