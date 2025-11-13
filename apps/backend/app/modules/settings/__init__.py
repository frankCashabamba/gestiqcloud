"""Settings Module - Gestión de Configuración Modular por Tenant"""

from .application.use_cases import SettingsManager
from .application.defaults import (
    get_default_settings,
    DEFAULT_SETTINGS_ES,
    DEFAULT_SETTINGS_EC,
)
from .application.modules_catalog import (
    get_available_modules,
    get_module_by_id,
    get_required_modules,
    get_default_enabled_modules,
    validate_module_dependencies,
    AVAILABLE_MODULES,
    MODULE_CATEGORIES,
)

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
