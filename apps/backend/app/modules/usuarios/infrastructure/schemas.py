from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UsuarioEmpresaBase(BaseModel):
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    email: EmailStr
    username: str | None = None


class UsuarioEmpresaCreate(UsuarioEmpresaBase):
    password: str = Field(min_length=8)
    active: bool = True
    es_admin_empresa: bool = False
    modulos: list[int] = Field(default_factory=list)
    roles: list[int] = Field(default_factory=list)


class UsuarioEmpresaUpdate(BaseModel):
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = Field(default=None, min_length=8)
    es_admin_empresa: bool | None = None
    active: bool | None = None
    modulos: list[int] | None = None
    roles: list[int] | None = None


class UsuarioEmpresaOut(UsuarioEmpresaBase):
    id: int
    tenant_id: int
    es_admin_empresa: bool
    active: bool
    modulos: list[int] = Field(default_factory=list)
    roles: list[int] = Field(default_factory=list)
    ultimo_login_at: datetime | None = None

    class Config:
        from_attributes = True


class ModuloOption(BaseModel):
    id: int
    name: str | None = None
    categoria: str | None = None
    icono: str | None = None


class RolEmpresaOption(BaseModel):
    id: int
    name: str
    description: str | None = None
