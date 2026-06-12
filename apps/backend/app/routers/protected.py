"""Compatibility shim: re-export router from modular location."""

from app.modules.identity.interface.http.protected import get_current_user, router

__all__ = ["router", "get_current_user"]
