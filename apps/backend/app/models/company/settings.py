"""Compatibility shim: exposes CompanySettings/InventorySettings under app.models.company.settings."""

from app.models.company.company_settings import CompanySettings, InventorySettings

# Legacy Spanish aliases
ConfiguracionEmpresa = CompanySettings
ConfiguracionInventario = InventorySettings

__all__ = [
    "CompanySettings",
    "InventorySettings",
    "ConfiguracionEmpresa",
    "ConfiguracionInventario",
]
