"""Compatibility shim: re-export sectors router from modular location."""
from app.modules.admin_config.interface.http.sectors import router

__all__ = ["router"]
