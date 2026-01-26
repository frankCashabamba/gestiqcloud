"""Compatibility shim: re-export router from modular location."""
from app.modules.users.interface.http.admin_usuarios import router

__all__ = ["router"]
