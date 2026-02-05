"""Compatibility shim: re-export router from modular location."""

from app.modules.admin_config.interface.http.sector_templates import router

__all__ = ["router"]
