"""Module: inventory_config.py

Auto-generated module docstring."""

# schemas/inventory_config.py

from pydantic import BaseModel, ConfigDict


class ConfiguracionInventarioBase(BaseModel):
    """Class ConfiguracionInventarioBase - auto-generated docstring."""

    stock_control_enabled: bool | None = True
    low_stock_notifications: bool | None = True
    global_minimum_stock: int | None = None
    default_units_of_measure: dict[str, list[str]] | None = None
    custom_categories_enabled: bool | None = False
    product_extra_fields: list[str] | None = None


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
