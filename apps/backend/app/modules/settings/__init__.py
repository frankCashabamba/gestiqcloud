"""Settings Module - Gestión de Configuración Modular por Tenant"""

from .application.defaults import DEFAULT_SETTINGS_EC, DEFAULT_SETTINGS_ES, get_default_settings
from .application.modules_catalog import (
    AVAILABLE_MODULES,
    MODULE_CATEGORIES,
    get_available_modules,
    get_default_enabled_modules,
    get_module_by_id,
    get_required_modules,
    validate_module_dependencies,
)
from .application.use_cases import SettingsManager

__all__ = [
    "SettingsManager",
    "get_default_settings",
    "DEFAULT_SETTINGS_ES",
    "DEFAULT_SETTINGS_EC",
    "get_available_modules",
    "get_module_by_id",
    "get_required_modules",
    "get_default_enabled_modules",
    "validate_module_dependencies",
    "AVAILABLE_MODULES",
    "MODULE_CATEGORIES",
]
