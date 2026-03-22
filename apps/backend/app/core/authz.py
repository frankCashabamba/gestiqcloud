# app/core/authz.py
from collections.abc import Iterable
from typing import Any

from fastapi import Depends, HTTPException

# Import lazy para evitar circular (access_guard no importa authz)
from app.core.access_guard import with_access_claims


def _permission_aliases(permission: str) -> list[str]:
    aliases = [permission]

    if "." not in permission:
        return aliases

    parts = permission.split(".")
    module = parts[0]
    action = parts[-1]

    if action in {"view", "read"}:
        aliases.append(f"{module}.read")
        aliases.append(f"{module}:read")
        aliases.append(f"{module}.view")
        aliases.append(f"{module}:view")
    elif action in {"create", "open"}:
        aliases.append(f"{module}.create")
        aliases.append(f"{module}:create")
    elif action in {"update", "manage", "close", "pay", "print"}:
        aliases.append(f"{module}.update")
        aliases.append(f"{module}:update")
    elif action in {"delete", "refund"}:
        aliases.append(f"{module}.delete")
        aliases.append(f"{module}:delete")

    return list(dict.fromkeys(aliases))


def require_scope(scope: str):
    """Verifica que el token tenga el scope/kind requerido.

    Usa with_access_claims como sub-dependencia para que FastAPI garantice
    que el token se parsea ANTES de validar el scope (evita 'Missing access claims').
    """

    def dep(claims: dict[str, Any] = Depends(with_access_claims)):
        kind = claims.get("kind")
        scope_claim = claims.get("scope")
        scopes_claim = claims.get("scopes")

        scopes: set[str] = set()
        if isinstance(scopes_claim, (list, tuple, set)):
            scopes.update(str(s) for s in scopes_claim if s)
        elif isinstance(scopes_claim, str) and scopes_claim.strip():
            scopes.add(scopes_claim.strip())

        # Accept either modern claim shape (kind) or legacy variants (scope/scopes).
        allowed = kind == scope or scope_claim == scope or scope in scopes
        if not allowed:
            raise HTTPException(status_code=403, detail="forbidden")
        return claims

    return dep


def require_roles(roles: Iterable[str], tenant_required: bool = False):
    roles_set = set(roles)

    def dep(claims: dict[str, Any] = Depends(with_access_claims)):
        user_roles = set(claims.get("roles", []))
        if tenant_required and not claims.get("tenant_id"):
            raise HTTPException(status_code=403, detail="forbidden")
        if not roles_set.intersection(user_roles):
            raise HTTPException(status_code=403, detail="forbidden")
        return claims

    return dep


def require_permission(permission: str):
    def dep(claims: dict[str, Any] = Depends(with_access_claims)):
        if (
            claims.get("is_company_admin")
            or claims.get("is_admin_company")
            or claims.get("es_admin_empresa")
        ):
            return claims
        perms = claims.get("permissions") or claims.get("permisos") or {}
        aliases = _permission_aliases(permission)
        if isinstance(perms, dict) and any(perms.get(alias) for alias in aliases):
            return claims
        available = sorted([k for k, v in perms.items() if v]) if isinstance(perms, dict) else []
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "missing_permission": permission,
                "accepted_aliases": aliases,
                "available_permissions": available,
            },
        )

    return dep
