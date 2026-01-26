"""SHIM: Backward compatibility - redirects to modules/admin_config/interface/http/migrations.py"""

from app.modules.admin_config.interface.http.migrations import router

__all__ = ["router"]
