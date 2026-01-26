"""Compatibility shim: re-export dashboard router from modular location."""

from app.modules.analytics.interface.http.tenant import router

__all__ = ["router"]
