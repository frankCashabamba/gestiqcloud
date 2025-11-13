"""Module: configuracion_empresa.py

Auto-generated module docstring."""

# schemas/configuracion_empresa.py

from pydantic import BaseModel, ConfigDict


class ConfiguracionEmpresaBase(BaseModel):
    """Class ConfiguracionEmpresaBase - auto-generated docstring."""

    idioma_predeterminado: str | None = "es"
    zona_horaria: str | None = "UTC"
    moneda: str | None = "USD"
    logo_empresa: str | None = None
    color_primario: str | None = "#4f46e5"
    color_secundario: str | None = "#6c757d"


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
