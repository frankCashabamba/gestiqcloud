"""Compatibility shim: re-export router from modular location."""

from app.modules.onboarding.interface.http.initial_config import router

__all__ = ["router"]
