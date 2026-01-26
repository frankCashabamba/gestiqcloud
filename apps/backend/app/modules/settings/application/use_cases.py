"""Settings Manager - Use Cases"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
from app.models.tenant import Tenant

from .modules_catalog import get_available_modules, get_module_by_id, validate_module_dependencies


class SettingsManager:
    """Settings Manager for Tenant and Module Configuration"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_settings(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """
        Get all settings for a tenant.

        Args:
            tenant_id: UUID of the tenant

        Returns:
            Dict with all configuration (creates defaults if not exists)
        """
        settings = (
            self.db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
        )

        if not settings:
            return {
                "id": None,
                "tenant_id": str(tenant_id),
                "locale": None,
                "timezone": None,
                "currency": None,
                "modules": {},
                "updated_at": None,
            }

        return {
            "id": str(settings.id),
            "tenant_id": str(settings.tenant_id),
            "locale": settings.default_language,
            "timezone": settings.timezone,
            "currency": settings.currency,
            "modules": settings.settings or {},
            "updated_at": settings.updated_at.isoformat(),
        }

    def get_module_settings(self, tenant_id: uuid.UUID, module: str) -> dict[str, Any]:
        """
        Get settings for a specific module.

        Args:
            tenant_id: UUID of the tenant
            module: Module ID (e.g. 'pos', 'inventory')

        Returns:
            Dict with module configuration
        """
        all_settings = self.get_all_settings(tenant_id)
        module_config = all_settings["modules"].get(module, {})

        # Check if the module exists in the catalog
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Module '{module}' does not exist")

        return {
            "module": module,
            "module_name": module_info["name"],
            "enabled": module_config.get("enabled", False),
            "config": module_config,
            "module_info": module_info,
        }

    def update_module_settings(
        self, tenant_id: uuid.UUID, module: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update module settings.

        Args:
            tenant_id: UUID of the tenant
            module: Module ID
            config: New configuration (merged with existing)

        Returns:
            Dict with updated configuration
        """
        # Check that the module exists
        if not get_module_by_id(module):
            raise ValueError(f"Module '{module}' does not exist")

        settings = (
            self.db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
        )

        if not settings:
            raise ValueError("company_settings_missing")

        # Merge configuration
        base_settings = settings.settings or {}
        current_config = base_settings.get(module, {}) if isinstance(base_settings, dict) else {}
        updated_config = {**current_config, **config}

        # Update in JSONB
        settings_dict = dict(base_settings) if isinstance(base_settings, dict) else {}
        settings_dict[module] = updated_config
        settings.settings = settings_dict
        settings.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(settings)

        return {
            "module": module,
            "config": updated_config,
            "updated_at": settings.updated_at.isoformat(),
        }

    def enable_module(self, tenant_id: uuid.UUID, module: str) -> dict[str, Any]:
        """
        Enable a module.

        Args:
            tenant_id: UUID of the tenant
            module: Module ID

        Returns:
            Dict with operation result
        """
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Module '{module}' does not exist")

        # Validate dependencies
        settings = self.get_all_settings(tenant_id)
        enabled_modules = [m for m, cfg in settings["modules"].items() if cfg.get("enabled", False)]

        # Add module to enable
        test_enabled = enabled_modules + [module]
        missing_deps = validate_module_dependencies(test_enabled)

        if module in missing_deps:
            return {
                "success": False,
                "module": module,
                "error": "missing_dependencies",
                "missing": missing_deps[module],
                "message": f"Missing dependencies: {', '.join(missing_deps[module])}",
            }

        # Enable module
        result = self.update_module_settings(tenant_id, module, {"enabled": True})

        return {
            "success": True,
            "module": module,
            "module_name": module_info["name"],
            "enabled": True,
            "updated_at": result["updated_at"],
        }

    def disable_module(self, tenant_id: uuid.UUID, module: str) -> dict[str, Any]:
        """
        Disable a module.

        Args:
            tenant_id: UUID of the tenant
            module: Module ID

        Returns:
            Dict with operation result
        """
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Module '{module}' does not exist")

        # Do not allow disabling required modules
        if module_info.get("required", False):
            return {
                "success": False,
                "module": module,
                "error": "module_required",
                "message": f"Module '{module_info['name']}' is required",
            }

        # Check that other modules do not depend on this one
        settings = self.get_all_settings(tenant_id)
        enabled_modules = [
            m for m, cfg in settings["modules"].items() if cfg.get("enabled", False) and m != module
        ]

        # Check inverse dependencies
        dependent_modules = []
        for enabled_mod in enabled_modules:
            mod_info = get_module_by_id(enabled_mod)
            if mod_info and module in mod_info.get("dependencies", []):
                dependent_modules.append(enabled_mod)

        if dependent_modules:
            return {
                "success": False,
                "module": module,
                "error": "module_has_dependents",
                "dependents": dependent_modules,
                "message": f"Other modules depend on this: {', '.join(dependent_modules)}",
            }

        # Disable module
        result = self.update_module_settings(tenant_id, module, {"enabled": False})

        return {
            "success": True,
            "module": module,
            "module_name": module_info["name"],
            "enabled": False,
            "updated_at": result["updated_at"],
        }

    def get_available_modules(self, tenant_id: uuid.UUID = None) -> list[dict[str, Any]]:
        """
        Get list of available modules.

        Args:
            tenant_id: UUID of the tenant (optional, to include enabled status)

        Returns:
            List of modules with metadata
        """
        country = None
        enabled_map = {}

        if tenant_id:
            # Get tenant country and enabled modules
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                country = tenant.country

            settings = self.get_all_settings(tenant_id)
            enabled_map = {m: cfg.get("enabled", False) for m, cfg in settings["modules"].items()}

        modules = get_available_modules(country)

        # Add enabled status if we have tenant_id
        if tenant_id:
            for module in modules:
                module["is_enabled"] = enabled_map.get(module["id"], False)

        return modules

    def init_default_settings(self, tenant_id: uuid.UUID, country: str = "ES") -> dict[str, Any]:
        """
        Initialize default settings for a tenant.

        Args:
            tenant_id: UUID of the tenant
            country: Country of the tenant ('ES' or 'EC')

        Returns:
            Dict with created configuration
        """
        # Check if already exists
        existing = (
            self.db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
        )

        if existing:
            return {
                "already_exists": True,
                "tenant_id": str(tenant_id),
                "message": "Settings already exist for this tenant",
            }

        return {
            "created": False,
            "tenant_id": str(tenant_id),
            "message": "Defaults are disabled; create company settings explicitly.",
        }

    def _create_default_settings(
        self, tenant_id: uuid.UUID, country: str = None
    ) -> CompanySettings:
        """
        Create default settings (internal use).

        Args:
            tenant_id: UUID of the tenant
            country: Country (auto-detected if not provided)

        Returns:
            CompanySettings instance
        """
        raise ValueError("defaults_disabled")
