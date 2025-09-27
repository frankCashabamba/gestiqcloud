"""Unified security surface for the app.

Re-exports selected utilities from existing modules to provide a stable
import path: `app.core.security`.
"""

try:  # pragmatic, keep imports resilient during refactors
    from app.core.auth_shared import (  # noqa: F401
        set_auth_cookies,
        clear_auth_cookies,
        issue_access_token,
        decode_access_token,
    )
except Exception:  # pragma: no cover
    pass

# Password hashing (expected by identity.infrastructure.passwords)
try:
    from passlib.context import CryptContext  # type: ignore

    _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(plain: str) -> str:  # noqa: D401 - simple facade
        """Hash a plaintext password using bcrypt."""
        return _pwd_ctx.hash(plain)

    def get_password_hash(plain: str) -> str:
        """Backward compatible alias used by legacy modules."""
        return hash_password(plain)

    def verify_password(plain: str, hashed: str):  # -> tuple[bool, str|None]
        try:
            ok = _pwd_ctx.verify(plain, hashed)
            return ok, None
        except Exception as e:  # keep signature used by callers
            return False, str(e)
except Exception:  # pragma: no cover
    pass

try:
    from app.core.csrf import ensure_csrf_token  # noqa: F401
except Exception:  # pragma: no cover
    pass

try:
    from app.core.permissions import require_permissions  # noqa: F401
except Exception:  # pragma: no cover
    pass

try:
    from app.core.access_guard import require_tenant, require_admin  # noqa: F401
except Exception:  # pragma: no cover
    pass
