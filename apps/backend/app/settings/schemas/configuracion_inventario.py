"""Module: configuracion_inventario.py

Auto-generated module docstring."""

# schemas/configuracion_inventario.py

from pydantic import BaseModel, ConfigDict


class ConfiguracionInventarioBase(BaseModel):
    """Class ConfiguracionInventarioBase - auto-generated docstring."""

    control_stock_activo: bool | None = True
    notificar_bajo_stock: bool | None = True
    stock_minimo_global: int | None = None
    um_predeterminadas: dict[str, list[str]] | None = None
    categorias_personalizadas: bool | None = False
    campos_extra_producto: list[str] | None = None


class ConfiguracionInventarioCreate(ConfiguracionInventarioBase):
    """Class ConfiguracionInventarioCreate - auto-generated docstring."""

    tenant_id: int


class ConfiguracionInventarioUpdate(ConfiguracionInventarioBase):
    """Class ConfiguracionInventarioUpdate - auto-generated docstring."""

    pass


class ConfiguracionInventarioOut(ConfiguracionInventarioBase):
    """Class ConfiguracionInventarioOut - auto-generated docstring."""

    id: int
    tenant_id: int

    model_config = ConfigDict(from_attributes=True)
