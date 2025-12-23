from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class CompanyInSchema(BaseModel):
    name: str = Field(min_length=1)
    slug: str | None = None
    tax_id: str | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = Field(default=None, validation_alias="cp")
    country: str | None = Field(default=None, validation_alias="pais")
    logo: str | None = None
    primary_color: str | None = Field(default=None, validation_alias="color_primario")
    active: bool | None = True
    deactivation_reason: str | None = Field(default=None, validation_alias="motivo_desactivacion")
    initial_template: str | None = Field(default=None, validation_alias="plantilla_inicio")
    website: str | None = Field(default=None, validation_alias="sitio_web")
    config_json: dict | None = None


class CompanyOutSchema(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    modules: list[str] = Field(default_factory=list, validation_alias="modulos")
