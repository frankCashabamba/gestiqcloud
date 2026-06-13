# app/core/authz.py
from collections.abc import Iterable
from typing import Any

from fastapi import Depends, HTTPException

# Import lazy para evitar circular (access_guard no importa authz)
from app.core.access_guard import with_access_claims


def _permission_aliases(permission: str) -> list[str]:
    aliases = [permission]
    explicit_aliases = {
        "accounting.entry.create": ["accounting:entry"],
        "accounting.entry.post": ["accounting:adjust"],
        "accounting.entry.cancel": ["accounting:adjust"],
        "accounting.account.manage": ["accounting:adjust"],
        "accounting.reports.read": ["accounting:read"],
        "quotes.manage": [
            "quotes:read",
            "quotes:create",
            "quotes:update",
            "quotes:delete",
            "quotes:manage",
        ],
        "pos.view": ["pos:read"],
        "pos.receipt.create": ["pos:write"],
        "pos.receipt.manage": ["pos:write"],
        "pos.receipt.pay": ["pos:cashier"],
        "pos.shift.open": ["pos:cashier"],
        "pos.shift.close": ["pos:close_shift"],
        "pos.receipt.refund": ["pos:refund"],
    }
    aliases.extend(explicit_aliases.get(permission, []))

    separator = "." if "." in permission else ":" if ":" in permission else ""
    if not separator:
        return aliases

    parts = permission.split(separator)
    module = parts[0]
    action = parts[-1]
    aliases.append(f"{module}.{action}")
    aliases.append(f"{module}:{action}")

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


def _has_permission(perms: dict[str, Any], permission: str) -> bool:
    if perms.get(permission) is True:
        return True

    split_index = max(permission.rfind("."), permission.rfind(":"))
    if split_index <= 0 or split_index >= len(permission) - 1:
        return False

    module = permission[:split_index]
    action = permission[split_index + 1 :]
    nested = perms.get(module)
    return isinstance(nested, dict) and nested.get(action) is True


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
        if isinstance(perms, dict) and any(_has_permission(perms, alias) for alias in aliases):
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
