"""Compatibility shim: re-export dashboard KPIs router under legacy path."""

from app.routers.dashboard_kpis import router

__all__ = ["router"]
