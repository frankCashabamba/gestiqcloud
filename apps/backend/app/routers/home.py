"""SHIM: Backward compatibility - redirects to modules/shared/interface/http/home.py"""

from app.modules.shared.interface.http.home import router

__all__ = ["router"]
