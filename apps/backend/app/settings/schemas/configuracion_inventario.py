"""Module: configuracion_inventario.py

Auto-generated module docstring."""

# schemas/configuracion_inventario.py

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ConfiguracionInventarioBase(BaseModel):
    """ Class ConfiguracionInventarioBase - auto-generated docstring. """
    control_stock_activo: Optional[bool] = True
    notificar_bajo_stock: Optional[bool] = True
    stock_minimo_global: Optional[int] = None
    um_predeterminadas: Optional[Dict[str, List[str]]] = None
    categorias_personalizadas: Optional[bool] = False
    campos_extra_producto: Optional[List[str]] = None

class ConfiguracionInventarioCreate(ConfiguracionInventarioBase):
    """ Class ConfiguracionInventarioCreate - auto-generated docstring. """
    empresa_id: int

class ConfiguracionInventarioUpdate(ConfiguracionInventarioBase):
    """ Class ConfiguracionInventarioUpdate - auto-generated docstring. """
    pass

class ConfiguracionInventarioOut(ConfiguracionInventarioBase):
    """ Class ConfiguracionInventarioOut - auto-generated docstring. """
    id: int
    empresa_id: int

    model_config = ConfigDict(from_attributes=True)
