"""Compatibility shim: re-export router from modular location."""
from app.modules.admin_config.interface.http.scripts import router

__all__ = ["router"]
