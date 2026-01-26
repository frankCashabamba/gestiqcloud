"""SHIM: Backward compatibility - redirects to modules/support/interface/http/incidents.py"""

from app.modules.support.interface.http.incidents import router

__all__ = ["router"]
