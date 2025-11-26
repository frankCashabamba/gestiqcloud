"""Module: configuracion_empresa.py

Auto-generated module docstring."""

# schemas/configuracion_empresa.py

from pydantic import BaseModel, ConfigDict


class ConfiguracionEmpresaBase(BaseModel):
    """Class ConfiguracionEmpresaBase - auto-generated docstring."""

    default_language: str | None = "es"
    timezone: str | None = "UTC"
    currency: str | None = "USD"
    company_logo: str | None = None
    primary_color: str | None = "#4f46e5"
    secondary_color: str | None = "#6c757d"


class ConfiguracionEmpresaCreate(ConfiguracionEmpresaBase):
    """Class ConfiguracionEmpresaCreate - auto-generated docstring."""

    tenant_id: int


class ConfiguracionEmpresaUpdate(ConfiguracionEmpresaBase):
    """Class ConfiguracionEmpresaUpdate - auto-generated docstring."""

    pass


class ConfiguracionEmpresaOut(ConfiguracionEmpresaBase):
    """Class ConfiguracionEmpresaOut - auto-generated docstring."""

    id: int
    tenant_id: int

    model_config = ConfigDict(from_attributes=True)
