"""Compatibility shim: re-export router from modular location."""
from app.modules.identity.interface.http.protected import router, get_current_user, decode_token, oauth2_scheme

__all__ = ["router", "get_current_user", "decode_token", "oauth2_scheme"]
