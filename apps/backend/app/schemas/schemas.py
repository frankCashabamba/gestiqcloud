"""Module: schemas.py

Auto-generated module docstring."""

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
    slug: str | None
    tipo_empresa_id: int | None
    tipo_negocio_id: int | None
    tax_id: str | None
    phone: str | None
    address: str | None
    city: str | None
    state: str | None
    cp: str | None
    pais: str | None
    logo: str | None
    color_primario: str | None = None
    plantilla_inicio: str | None = None
    sitio_web: str | None
    config_json: dict | None
    modulos: list[int] | None = []


class EmpresaConUsuarioCreate(BaseModel):
    """Class EmpresaConUsuarioCreate - auto-generated docstring."""

    empresa: EmpresaCreate
    usuario: UsuarioCreate
