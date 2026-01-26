"""Compatibility shim: re-export roles router from modular location."""

from app.modules.identity.interface.http.roles import router

__all__ = ["router"]
