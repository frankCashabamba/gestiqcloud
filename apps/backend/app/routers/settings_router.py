"""Compatibility shim: re-export router from modular location."""

from app.modules.settings.interface.http.settings_router import router

__all__ = ["router"]
