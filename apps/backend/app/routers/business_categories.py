"""Compatibility shim: re-export router from modular location."""

from app.modules.admin_config.interface.http.business_categories import router

__all__ = ["router"]
