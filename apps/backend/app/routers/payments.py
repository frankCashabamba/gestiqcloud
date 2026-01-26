"""Compatibility shim: re-export router from modular location."""

from app.modules.reconciliation.interface.http.payments import router

__all__ = ["router"]
