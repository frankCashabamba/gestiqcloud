"""Compatibility wrapper exposing Tenant as Empresa for legacy imports."""

from app.models.tenant import Tenant as Empresa

__all__ = ["Empresa"]
