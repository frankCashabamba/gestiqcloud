
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UsuarioEmpresaBase(BaseModel):
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    email: EmailStr
    username: str | None = None


class UsuarioEmpresaCreate(UsuarioEmpresaBase):
    password: str = Field(min_length=8)
    activo: bool = True
    es_admin_empresa: bool = False
    modulos: List[int] = Field(default_factory=list)
    roles: List[int] = Field(default_factory=list)


class UsuarioEmpresaUpdate(BaseModel):
    nombre_encargado: Optional[str] = None
    apellido_encargado: Optional[str] = None
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    es_admin_empresa: Optional[bool] = None
    activo: Optional[bool] = None
    modulos: Optional[List[int]] = None
    roles: Optional[List[int]] = None


class UsuarioEmpresaOut(UsuarioEmpresaBase):
    id: int
    empresa_id: int
    es_admin_empresa: bool
    activo: bool
    modulos: List[int] = Field(default_factory=list)
    roles: List[int] = Field(default_factory=list)
    ultimo_login_at: datetime | None = None

    class Config:
        from_attributes = True


class ModuloOption(BaseModel):
    id: int
    nombre: str | None = None
    categoria: str | None = None
    icono: str | None = None


class RolEmpresaOption(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None

