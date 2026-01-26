"""SHIM: Backward compatibility - redirects to modules/shared/interface/http/listings.py"""

from app.modules.shared.interface.http.listings import router

__all__ = ["router"]
