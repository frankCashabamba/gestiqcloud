"""Compatibility shim: re-export router from modular location."""
from app.modules.analytics.interface.http.admin import router

__all__ = ["router"]
