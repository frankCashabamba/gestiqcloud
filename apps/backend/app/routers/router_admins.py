"""Compatibility shim: re-export router from modular location."""

from app.modules.users.interface.http.router_admins import router

__all__ = ["router"]
