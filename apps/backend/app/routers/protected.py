"""Compatibility shim: re-export router from modular location."""

from app.modules.identity.interface.http.protected import (
    decode_token,
    get_current_user,
    oauth2_scheme,
    router,
)

__all__ = ["router", "get_current_user", "decode_token", "oauth2_scheme"]
