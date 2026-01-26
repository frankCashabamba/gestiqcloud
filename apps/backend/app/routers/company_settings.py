"""Compatibility shim: re-export company settings router from modular location."""
from app.modules.settings.interface.http.company import router, router_admin

__all__ = ["router", "router_admin"]
