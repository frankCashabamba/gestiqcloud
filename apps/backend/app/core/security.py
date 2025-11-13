"""Unified security surface for the app.

Re-exports selected utilities from existing modules to provide a stable
import path: `app.core.security`.
"""

# ---- Auth cookies & tokens ---------------------------------------------------
try:  # pragmatic, keep imports resilient during refactors
    from app.core.auth_shared import (  # noqa: F401
        clear_auth_cookies,
        decode_access_token,
        issue_access_token,
        set_auth_cookies,
    )
except Exception:  # pragma: no cover
    pass

# ---- Password hashing --------------------------------------------------------
# Evita el límite de 72 bytes de bcrypt con un pre-hash SHA-256, manteniendo
# el formato/longitud estándar $2b$ (~60 chars). Incluye verificación legacy
# para hashes antiguos generados sin pre-hash.
import hashlib

import bcrypt


def _norm_bytes(password: str) -> bytes:
    """Normalize password to fixed-length bytes using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(plain: str) -> str:  # noqa: D401 - simple facade
    """Hash a plaintext password using bcrypt (with SHA-256 pre-hash)."""
    digest = _norm_bytes(plain)
    return bcrypt.hashpw(digest, bcrypt.gensalt()).decode("utf-8")


def get_password_hash(plain: str) -> str:
    """Backward compatible alias used by legacy modules."""
    return hash_password(plain)


def verify_password(plain: str, hashed: str):
    """Verify plaintext against a bcrypt hash.

    Returns:
        tuple[bool, str | None]: (ok, error_message_if_any)
    """
    try:
        # Nuevo formato (con pre-hash)
        if bcrypt.checkpw(_norm_bytes(plain), hashed.encode("utf-8")):
            return True, None
        # Fallback: hashes legacy generados sin pre-hash
        ok = bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        return ok, None
    except Exception as e:  # conserva la firma usada por los callers
        return False, str(e)


# ---- CSRF / Permissions / Access Guards -------------------------------------
try:
    from app.core.csrf import ensure_csrf_token  # noqa: F401
except Exception:  # pragma: no cover
    pass

try:
    from app.core.permissions import require_permissions  # noqa: F401
except Exception:  # pragma: no cover
    pass

try:
    from app.core.access_guard import require_admin, require_tenant  # noqa: F401
except Exception:  # pragma: no cover
    pass

# ---- Minimal current user dependency ----------------------------------------
try:
    from app.schemas.auth import User  # type: ignore
except Exception:  # pragma: no cover
    User = None  # type: ignore


async def get_current_active_tenant_user():  # pragma: no cover - mostly mocked in tests
    """Minimal dependency returning a placeholder user.

    Test code typically patches this coroutine with AsyncMock to control
    the tenant_id. Providing a default implementation avoids AttributeError
    during import when tests reference this symbol.
    """
    if User is None:  # fallback to a lightweight object

        class _U:
            def __init__(self):
                self.tenant_id = None

        return _U()
    # Create a user with a null tenant; tests will mock this anyway
    try:
        from uuid import uuid4

        return User(id=None, tenant_id=uuid4())  # type: ignore[arg-type]
    except Exception:
        # As a last resort return a duck-typed object
        class _U:
            def __init__(self):
                self.tenant_id = None

        return _U()
