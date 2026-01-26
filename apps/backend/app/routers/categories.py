"""Compatibility shim: re-export router from modular location."""
from app.modules.products.interface.http.categories import router

__all__ = ["router"]
