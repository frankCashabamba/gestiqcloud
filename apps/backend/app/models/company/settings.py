"""Compatibility shim: exposes CompanySettings/InventorySettings under app.models.company.settings."""

from app.models.company.company_settings import CompanySettings, InventorySettings

__all__ = ["CompanySettings", "InventorySettings"]
