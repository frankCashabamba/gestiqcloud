"""Tenant middleware/dependencies — SHIM de compatibilidad.

⚠️ Este módulo era una copia byte-a-byte de `app/core/auth_dependencies.py`.
Para evitar dos implementaciones divergentes, ahora **re-exporta** desde el
hogar oficial. No añadir lógica aquí: el contrato de auth vive en
`app/core/auth_dependencies.py` (wrappers) y `app/core/access_guard.py`
(`with_access_claims`, única puerta de validación de token).

Ver `docs/security/auth-contract.md`.
"""

from __future__ import annotations

from app.core.auth_dependencies import (
    _validate_tenant_uuid,
    ensure_tenant,
    get_current_user,
)

__all__ = ["ensure_tenant", "get_current_user", "_validate_tenant_uuid"]
