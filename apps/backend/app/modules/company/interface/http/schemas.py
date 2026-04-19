from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.shared.jsonb_schemas import TenantConfigJSON


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
    config_json: TenantConfigJSON | None = None

    @field_validator("config_json", mode="before")
    @classmethod
    def validate_config_json(cls, v: Any) -> Any:
        """Acepta dict genérico pero rechaza tipos no-dict y valida 'features'."""
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("config_json debe ser un objeto JSON (dict)")
        features = v.get("features")
        if features is not None and not isinstance(features, dict):
            raise ValueError("config_json.features debe ser un objeto {flag: bool}")
        if isinstance(features, dict):
            invalid = {k: val for k, val in features.items() if not isinstance(val, bool)}
            if invalid:
                raise ValueError(
                    f"config_json.features: los valores deben ser booleanos, "
                    f"encontrado {invalid}"
                )
        return v


class CompanyOutSchema(BaseModel):
    id: UUID
    name: str
    slug: str | None = None
    modules: list[str] = Field(default_factory=list, validation_alias="modulos")
