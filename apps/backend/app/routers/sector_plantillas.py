"""Compatibility shim: re-export router from modular location."""
from app.modules.admin_config.interface.http.sector_plantillas import router

__all__ = ["router"]
