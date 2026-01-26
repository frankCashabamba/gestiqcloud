"""Compatibility shim: re-export router from modular location."""
from app.modules.identity.interface.http.tenant_roles import router

__all__ = ["router"]
