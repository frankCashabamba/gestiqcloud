"""Module: configuracionempresasinicial.py

Auto-generated module docstring."""

# schemas/configuracion.py

# Única fuente de verdad migrada a settings/schemas/configuracion_empresa.py
# Mantiene compatibilidad pública re-exportando el nombre aquí.
from pydantic import BaseModel, ConfigDict

from app.settings.schemas.configuracion_empresa import (  # noqa: F401
    ConfiguracionEmpresaCreate as ConfiguracionEmpresaCreate,
)


class EmpresaConfiguracionOut(BaseModel):
    """Class EmpresaConfiguracionOut - auto-generated docstring."""

    logo_empresa: str | None = None
    color_primario: str | None = None
    color_secundario: str | None = None
    empresa_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True)
