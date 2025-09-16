"""Module: configuracionempresasinicial.py

Auto-generated module docstring."""

# schemas/configuracion.py
from typing import Optional

from pydantic import BaseModel


class ConfiguracionEmpresaCreate(BaseModel):
    """ Class ConfiguracionEmpresaCreate - auto-generated docstring. """
    idioma_predeterminado: str
    zona_horaria: str
    moneda: Optional[str] = "USD"
    logo_empresa: Optional[str] = None
    color_secundario: Optional[str] = "#6c757d"
    color_primario: Optional[str] = "#4f46e5"


class EmpresaConfiguracionOut(BaseModel):
    """ Class EmpresaConfiguracionOut - auto-generated docstring. """
    logo_empresa: Optional[str] = None
    color_primario: Optional[str] = "#4f46e5"
    color_secundario: Optional[str] = "#6c757d"
    empresa_nombre: Optional[str] = None

    class Config:
        """ Class Config - auto-generated docstring. """
        from_attributes = True