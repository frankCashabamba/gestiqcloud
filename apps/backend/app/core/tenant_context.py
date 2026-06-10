"""Tenant context único.

Fuente de verdad para resolver QUIÉN hace la request y a QUÉ tenant pertenece.
Toda la información parte de `with_access_claims` (la única puerta de validación
de token; ver `docs/security/auth-contract.md`).

Las funciones legacy que extraían tenant_id por su cuenta
(`get_tenant_uuid`, `get_tenant_id_from_token`, `get_current_tenant_id`,
`tenant_id_from_request`, ...) ahora delegan aquí. Ver
`docs/security/tenant-context-contract.md`.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import Request
from pydantic import BaseModel

Scope = Literal["tenant", "admin", "public"]


class TenantContext(BaseModel):
    """Contexto tipado de la request. `scope` distingue plataforma/tenant/anónimo."""

    tenant_id: UUID | None = None
    user_id: UUID | None = None
    scope: Scope = "public"
    is_superadmin: bool = False
    request_id: str | None = None


def _coerce_uuid(value) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def get_tenant_context(request: Request, *, allow_session_fallback: bool = True) -> TenantContext:
    """Resuelve el `TenantContext` de la request.

    No lanza excepción: si no hay identidad devuelve `scope="public"`. Los
    dependencies que exijan tenant deben validar `ctx.tenant_id is not None`.

    Orden de resolución:
      1. `request.state.access_claims` (si ya lo puso `with_access_claims`).
      2. `with_access_claims(request)` (sin relanzar si falta token).
      3. Fallback opcional a `request.state.session` (compat admin UI legacy).
    """
    claims = getattr(request.state, "access_claims", None)
    if not isinstance(claims, dict):
        try:
            from app.core.access_guard import with_access_claims

            claims = with_access_claims(request)
        except Exception:
            claims = {}
    claims = claims if isinstance(claims, dict) else {}

    tenant_id = _coerce_uuid(claims.get("tenant_id") or claims.get("empresa_id"))
    user_id = _coerce_uuid(claims.get("user_id") or claims.get("sub"))
    kind = claims.get("kind") or claims.get("scope")
    is_superadmin = bool(claims.get("is_superadmin"))

    if allow_session_fallback and (tenant_id is None or user_id is None):
        sess = getattr(request.state, "session", None) or {}
        if isinstance(sess, dict):
            tenant_id = tenant_id or _coerce_uuid(sess.get("tenant_id"))
            user_id = user_id or _coerce_uuid(sess.get("tenant_user_id"))

    if kind == "admin":
        scope: Scope = "admin"
    elif tenant_id is not None:
        scope = "tenant"
    else:
        scope = "public"

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        scope=scope,
        is_superadmin=is_superadmin,
        request_id=getattr(request.state, "request_id", None),
    )
