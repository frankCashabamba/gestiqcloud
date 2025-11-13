"""Module: configuracion_empresa.py

Auto-generated module docstring."""

# schemas/configuracion_empresa.py

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ConfiguracionEmpresaBase(BaseModel):
    """Class ConfiguracionEmpresaBase - auto-generated docstring."""

    idioma_predeterminado: Optional[str] = "es"
    zona_horaria: Optional[str] = "UTC"
    moneda: Optional[str] = "USD"
    logo_empresa: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"
    color_secundario: Optional[str] = "#6c757d"


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
