# app/core/authz.py
from collections.abc import Iterable

from fastapi import HTTPException, Request


def _extract_claims(request: Request) -> dict:
    # Ajusta si usas otro lugar; asumo que ya parseas el access y lo pones en request.state
    claims = getattr(request.state, "access_claims", None)
    if not claims:
        raise HTTPException(status_code=401, detail="Missing access claims")
    return claims


def require_scope(scope: str):
    def dep(request: Request):
        claims = _extract_claims(request)
        if claims.get("kind") != scope:
            raise HTTPException(status_code=403, detail="forbidden")
        return claims

    return dep


def require_roles(roles: Iterable[str], tenant_required: bool = False):
    roles_set = set(roles)

    def dep(request: Request):
        claims = _extract_claims(request)
        user_roles = set(claims.get("roles", []))
        if tenant_required and not claims.get("tenant_id"):
            raise HTTPException(status_code=403, detail="forbidden")
        if not roles_set.intersection(user_roles):
            raise HTTPException(status_code=403, detail="forbidden")
        return claims

    return dep
