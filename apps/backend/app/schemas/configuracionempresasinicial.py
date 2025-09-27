"""Module: configuracionempresasinicial.py

Auto-generated module docstring."""

# schemas/configuracion.py
from typing import Optional

from pydantic import BaseModel, ConfigDict

# Única fuente de verdad migrada a settings/schemas/configuracion_empresa.py
# Mantiene compatibilidad pública re-exportando el nombre aquí.
from app.settings.schemas.configuracion_empresa import (
    ConfiguracionEmpresaCreate as ConfiguracionEmpresaCreate,  # noqa: F401
)


class EmpresaConfiguracionOut(BaseModel):
    """ Class EmpresaConfiguracionOut - auto-generated docstring. """
    logo_empresa: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"
    color_secundario: Optional[str] = "#6c757d"
    empresa_nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
