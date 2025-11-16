from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator
from typing import Annotated


class UsuarioEmpresaBase(BaseModel):
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    email: EmailStr
    username: str | None = None


class UsuarioEmpresaCreate(UsuarioEmpresaBase):
    password: str = Field(min_length=8)
    active: bool = Field(default=True, alias="activo")
    es_admin_empresa: bool = False
    modulos: list[UUID] = Field(default_factory=list)
    roles: list[UUID] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UsuarioEmpresaUpdate(BaseModel):
    nombre_encargado: str | None = None
    apellido_encargado: str | None = None
    email: EmailStr | None = None
    username: str | None = None
    password: str | None = Field(default=None, min_length=8)
    es_admin_empresa: bool | None = None
    active: bool | None = Field(default=None, alias="activo")
    modulos: list[UUID] | None = None
    roles: list[UUID] | None = None

    model_config = ConfigDict(populate_by_name=True)


class UsuarioEmpresaOut(UsuarioEmpresaBase):
    id: UUID
    tenant_id: UUID
    es_admin_empresa: bool
    active: bool = Field(validation_alias="activo")
    modulos: list[UUID] = Field(default_factory=list)
    roles: list[UUID] = Field(default_factory=list)
    ultimo_login_at: datetime | None = Field(default=None, alias="last_login_at")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ModuloOption(BaseModel):
    id: UUID
    name: str | None = None
    categoria: str | None = None
    icono: str | None = None


class RolEmpresaOption(BaseModel):
    id: UUID
    name: str
    description: str | None = None
