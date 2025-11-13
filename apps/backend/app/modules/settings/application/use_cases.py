"""Settings Manager - Use Cases"""

import uuid
from datetime import datetime
from typing import Any

from app.models.core.settings import TenantSettings
from app.models.tenant import Tenant
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .defaults import get_default_settings
from .modules_catalog import get_available_modules, get_module_by_id, validate_module_dependencies


class SettingsManager:
    """Gestor de Settings por Tenant y Módulo"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_settings(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """
        Obtener todas las configuraciones de un tenant

        Args:
            tenant_id: UUID del tenant

        Returns:
            Dict con toda la configuración (crea defaults si no existe)
        """
        settings = (
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if not settings:
            # Auto-crear settings con defaults
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
        Obtener configuración de un módulo específico

        Args:
            tenant_id: UUID del tenant
            module: ID del módulo (ej: 'pos', 'inventory')

        Returns:
            Dict con configuración del módulo
        """
        all_settings = self.get_all_settings(tenant_id)
        module_config = all_settings["modules"].get(module, {})

        # Verificar si el módulo existe en el catálogo
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Módulo '{module}' no existe")

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
        Actualizar configuración de un módulo

        Args:
            tenant_id: UUID del tenant
            module: ID del módulo
            config: Nueva configuración (se hace merge con existente)

        Returns:
            Dict con configuración actualizada
        """
        # Verificar que el módulo exista
        if not get_module_by_id(module):
            raise ValueError(f"Módulo '{module}' no existe")

        settings = (
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if not settings:
            settings = self._create_default_settings(tenant_id)

        # Merge de configuración
        current_config = settings.settings.get(module, {})
        updated_config = {**current_config, **config}

        # Actualizar en JSONB
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
        Habilitar un módulo

        Args:
            tenant_id: UUID del tenant
            module: ID del módulo

        Returns:
            Dict con resultado de la operación
        """
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Módulo '{module}' no existe")

        # Validar dependencias
        settings = self.get_all_settings(tenant_id)
        enabled_modules = [m for m, cfg in settings["modules"].items() if cfg.get("enabled", False)]

        # Agregar el módulo a habilitar
        test_enabled = enabled_modules + [module]
        missing_deps = validate_module_dependencies(test_enabled)

        if module in missing_deps:
            return {
                "success": False,
                "module": module,
                "error": "missing_dependencies",
                "missing": missing_deps[module],
                "message": f"Faltan dependencias: {', '.join(missing_deps[module])}",
            }

        # Habilitar módulo
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
        Deshabilitar un módulo

        Args:
            tenant_id: UUID del tenant
            module: ID del módulo

        Returns:
            Dict con resultado de la operación
        """
        module_info = get_module_by_id(module)
        if not module_info:
            raise ValueError(f"Módulo '{module}' no existe")

        # No permitir deshabilitar módulos obligatorios
        if module_info.get("required", False):
            return {
                "success": False,
                "module": module,
                "error": "module_required",
                "message": f"El módulo '{module_info['name']}' es obligatorio",
            }

        # Verificar que otros módulos no dependan de este
        settings = self.get_all_settings(tenant_id)
        enabled_modules = [
            m for m, cfg in settings["modules"].items() if cfg.get("enabled", False) and m != module
        ]

        # Verificar dependencias inversas
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
                "message": f"Otros módulos dependen de este: {', '.join(dependent_modules)}",
            }

        # Deshabilitar módulo
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
        Obtener lista de módulos disponibles

        Args:
            tenant_id: UUID del tenant (opcional, para incluir estado enabled)

        Returns:
            Lista de módulos con metadata
        """
        country = None
        enabled_map = {}

        if tenant_id:
            # Obtener país del tenant y módulos habilitados
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            if tenant:
                country = tenant.country

            settings = self.get_all_settings(tenant_id)
            enabled_map = {m: cfg.get("enabled", False) for m, cfg in settings["modules"].items()}

        modules = get_available_modules(country)

        # Agregar estado de habilitación si tenemos tenant_id
        if tenant_id:
            for module in modules:
                module["is_enabled"] = enabled_map.get(module["id"], False)

        return modules

    def init_default_settings(self, tenant_id: uuid.UUID, country: str = "ES") -> dict[str, Any]:
        """
        Inicializar configuración por defecto para un tenant

        Args:
            tenant_id: UUID del tenant
            country: País del tenant ('ES' o 'EC')

        Returns:
            Dict con configuración creada
        """
        # Verificar si ya existe
        existing = (
            self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
        )

        if existing:
            return {
                "already_exists": True,
                "tenant_id": str(tenant_id),
                "message": "Settings ya existen para este tenant",
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
        Crear settings por defecto (uso interno)

        Args:
            tenant_id: UUID del tenant
            country: País (detecta automáticamente si no se provee)

        Returns:
            Instancia de TenantSettings
        """
        # Detectar país del tenant si no se provee
        if not country:
            tenant = self.db.query(Tenant).filter(Tenant.id == tenant_id).first()
            country = tenant.country if tenant else "ES"

        # Obtener defaults según país
        defaults = get_default_settings(country)
        global_config = defaults.pop("global", {})

        # Crear settings
        settings = TenantSettings(
            tenant_id=tenant_id,
            locale=global_config.get("locale", "es"),
            timezone=global_config.get("timezone", "Europe/Madrid"),
            currency=global_config.get("currency", "EUR"),
            settings=defaults,  # Todos los módulos
        )

        self.db.add(settings)
        try:
            self.db.commit()
            self.db.refresh(settings)
        except IntegrityError:
            self.db.rollback()
            # Si falla por duplicado, obtener el existente
            settings = (
                self.db.query(TenantSettings).filter(TenantSettings.tenant_id == tenant_id).first()
            )

        return settings
