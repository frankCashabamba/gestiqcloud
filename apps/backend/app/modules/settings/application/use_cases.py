"""Settings Manager - Use Cases"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.core.settings import TenantSettings
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
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if not settings:
            # Auto-create settings with defaults
            settings = self._create_default_settings(tenant_id)

        return {
            "id": str(settings.id),
            "tenant_id": str(settings.tenant_id),
            "locale": settings.locale,
            "timezone": settings.timezone,
            "currency": settings.currency,
            "modules": settings.settings,
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
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if not settings:
            settings = self._create_default_settings(tenant_id)

        # Merge configuration
        current_config = settings.settings.get(module, {})
        updated_config = {**current_config, **config}

        # Update in JSONB
        settings_dict = dict(settings.settings)
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
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if existing:
            return {
                "already_exists": True,
                "tenant_id": str(tenant_id),
                "message": "Settings already exist for this tenant",
            }

        settings = self._create_default_settings(tenant_id, country)

        return {
            "created": True,
            "tenant_id": str(settings.tenant_id),
            "locale": settings.locale,
            "timezone": settings.timezone,
            "currency": settings.currency,
            "modules_count": len(settings.settings),
            "created_at": settings.updated_at.isoformat(),
        }

    def _create_default_settings(self, tenant_id: uuid.UUID, country: str = None) -> TenantSettings:
        """
        Create default settings (internal use).

        Args:
            tenant_id: UUID of the tenant
            country: Country (auto-detected if not provided)

        Returns:
            TenantSettings instance
        """
        # Detect tenant country if not provided
        if not country:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                country = tenant.country_code or tenant.country

        settings_kwargs: dict[str, Any] = {"tenant_id": tenant_id}
        if tenant and getattr(tenant, "base_currency", None):
            settings_kwargs["currency"] = tenant.base_currency
        settings_kwargs["settings"] = {}

        # Create settings
        settings = TenantSettings(**settings_kwargs)

        self.db.add(settings)
        try:
            self.db.commit()
            self.db.refresh(settings)
        except IntegrityError:
            self.db.rollback()
            # If it fails due to duplicate, get the existing one
            settings = (
                self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
            )

        return settings
