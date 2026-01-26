"""Compatibility shim: re-export onboarding router from modular location."""

from app.modules.onboarding.interface.http.tenant import router

__all__ = ["router"]
