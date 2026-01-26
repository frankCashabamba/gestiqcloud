"""Compatibility shim: re-export router from modular location."""

from app.modules.users.interface.http.tenant_usuarios import router

__all__ = ["router"]
