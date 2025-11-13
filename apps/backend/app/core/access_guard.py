# app/core/access_guard.py
from typing import Any

from app.config.database import SessionLocal
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from fastapi import HTTPException, Request
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import text

token_service = PyJWTTokenService()


def with_access_claims(request: Request) -> dict[str, Any]:
    # 1) extrae Authorization
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        claims = token_service.decode_and_validate(token, expected_type="access")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired") from None
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="Invalid token payload")
    # ValidaciÃ³n opcional: X-Tenant-Slug debe corresponder al tenant del token
    try:
        tenant_slug = (request.headers.get("X-Tenant-Slug") or "").strip()
        if tenant_slug:
            # Soporta tokens con tenant_id como tenant_id (int) o UUID segÃºn despliegue
            tid = (
                str(claims.get("tenant_id"))
                if isinstance(claims, dict) and claims.get("tenant_id") is not None
                else None
            )
            if tid:
                # Primero intenta tenants.slug si tid es numÃ©rico
                ok = False
                if tid.isdigit():
                    try:
                        with SessionLocal() as db:
                            row = db.execute(
                                text("SELECT slug FROM tenants WHERE tenant_id=:id"),
                                {"id": int(tid)},
                            ).first()
                            ok = bool(row and row[0] and str(row[0]).strip() == tenant_slug)
                    except Exception:
                        ok = False
                # Si no ok y hay tabla tenants, valida contra tenants.slug
                if not ok:
                    try:
                        with SessionLocal() as db:
                            # tid puede ser UUID; compara por id::text o por tenant_id si es dÃ­gito
                            if tid.isdigit():
                                row = db.execute(
                                    text("SELECT slug FROM tenants WHERE tenant_id =:id"),
                                    {"id": int(tid)},
                                ).first()
                            else:
                                row = db.execute(
                                    text("SELECT slug FROM tenants WHERE tenant_id =:id"),
                                    {"id": tid},
                                ).first()
                            ok = bool(row and row[0] and str(row[0]).strip() == tenant_slug)
                    except Exception:
                        ok = False
                if not ok:
                    raise HTTPException(status_code=403, detail="tenant_slug_mismatch")
    except HTTPException:
        raise
    except Exception:
        # No romper si la validaciÃ³n no se puede realizar
        pass

    request.state.access_claims = claims
    return claims
