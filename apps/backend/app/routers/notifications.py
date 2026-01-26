"""Compatibility shim: re-export notifications router from modular location."""

from app.modules.notifications.interface.http.tenant import router

__all__ = ["router"]
