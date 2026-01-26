"""Compatibility shim: re-export router from modular location."""
from app.modules.settings.interface.http.public import router

__all__ = ["router"]
