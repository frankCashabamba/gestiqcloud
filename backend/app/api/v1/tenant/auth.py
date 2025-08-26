from typing import Mapping, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.perm_loader import build_tenant_claims
from app.core.i18n import t
from app.core.audit import audit as audit_log
from app.config.database import get_db
from app.core.security import verify_password
from app.core.csrf import issue_csrf_token
from app.core.deps import set_tenant_scope
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.config.settings import settings

from app.core.refresh import (
    family_create,
    token_issue,
    create_access,
    create_refresh,
    token_mark_used,
    token_is_reused_or_revoked,
    family_revoke,
    token_get_family,
    decode_and_validate,
)

from app.core.login_rate_limit import check as rl_check, incr_fail as rl_fail, reset as rl_reset

from app.core.auth_http import (
    set_refresh_cookie,
    delete_auth_cookies,
    best_effort_family_revoke,
    refresh_cookie_path_tenant,  # <- IMPORT NECESARIO
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginTenant(BaseModel):
    identificador: str
    password: str


@router.post("/login")
def tenant_login(
    data: LoginTenant,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    ident = data.identificador.strip().lower()

    # 0) Rate limiting
    rl = rl_check(request, ident)
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail=t(request, "too_many_attempts"),
            headers={"Retry-After": str(rl.retry_after)} if rl.retry_after else None,
        )
    if rl.retry_after:
        response.headers["Retry-After"] = str(rl.retry_after)

    # 1) Buscar usuario (case-insensitive) + join con empresa
    user = (
        db.query(UsuarioEmpresa)
        .options(joinedload(UsuarioEmpresa.empresa))
        .filter(
            or_(
                func.lower(UsuarioEmpresa.email) == ident,
                func.lower(UsuarioEmpresa.username) == ident,
            )
        )
        .first()
    )

    # 2) Validaciones básicas
    if not user or not user.empresa_id or not user.empresa:
        rl_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=None, tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    ok, new_hash = verify_password(data.password, user.password_hash)
    if not ok:
        rl_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=str(user.id), tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # Rehash transparente si procede
    if new_hash:
        user.password_hash = new_hash
        db.add(user)
        db.commit()

    # OK → resetea contador
    rl_reset(request, ident)

    tenant_id = str(user.empresa.id)

    # 3) Sesión + scope
    if not hasattr(request, "state") or not hasattr(request.state, "session"):
        request.state.session = {}
    request.state.session.update(
        {"kind": "tenant", "tenant_user_id": str(user.id), "tenant_id": tenant_id}
    )
    request.state.session_dirty = True
    set_tenant_scope(request, tenant_id)

    # 4) CSRF (cookie legible por JS)
    csrf = issue_csrf_token(request)
    response.set_cookie(
        "csrf_token",
        csrf,
        httponly=False,
        samesite="lax",
        secure=not settings.debug,
    )

    # Claims (permisos, tenant, etc.)
    claims = build_tenant_claims(db, user)
    if not claims:
        rl_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=str(user.id), tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # 5) Refresh family + primer token
    family_id = family_create(user_id=str(user.id), tenant_id=tenant_id)
    jti = token_issue(
        family_id,
        prev_jti=None,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    # 6) JWTs (devuelven strings)
    access = create_access(claims)
    refresh = create_refresh(
        {
            "sub": claims["sub"],
            "user_id": claims["user_id"],
            "kind": "tenant",
            "family_id": family_id,
        },
        jti=jti,
        prev_jti=None,
    )

    # 7) Cookie refresh (pasa el string, no .token)
    set_refresh_cookie(response, refresh, path=refresh_cookie_path_tenant())

    # Auditoría de éxito
    audit_log(
        db,
        kind="login",
        scope="tenant",
        user_id=str(user.id),
        tenant_id=tenant_id,
        req=request,
    )

    return {
        "access_token": access,
        "token_type": "bearer",
        "scope": "tenant",
        "tenant_id": claims.get("tenant_id"),
        "empresa_slug": claims.get("empresa_slug"),
        "plantilla": claims.get("plantilla"),
        "es_admin_empresa": claims.get("es_admin_empresa"),
    }


@router.post("/refresh")
def tenant_refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    try:
        payload: Mapping[str, object] = decode_and_validate(token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    # jti debe ser str
    jti_obj = payload.get("jti")
    if not isinstance(jti_obj, str) or not jti_obj:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))
    jti: str = jti_obj

    # family_id desde DB o del payload
    family_from_db: Optional[str] = token_get_family(jti)
    fam_payload_obj = payload.get("family_id")
    fam_payload: Optional[str] = fam_payload_obj if isinstance(fam_payload_obj, str) else None
    family_id: Optional[str] = family_from_db or fam_payload
    if family_id is None:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    # Reuse / revoked / used
    if token_is_reused_or_revoked(jti):
        family_revoke(family_id)
        raise HTTPException(status_code=401, detail=t(request, "compromised_refresh_token"))

    # Rotación
    token_mark_used(jti)
    new_jti = token_issue(
        family_id=family_id,
        prev_jti=jti,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    minimal = {"sub": payload.get("sub"), "user_id": payload.get("user_id")}
    access = create_access({**minimal, "kind": "tenant"})
    new_refresh = create_refresh(
        {**minimal, "kind": "tenant", "family_id": family_id},
        jti=new_jti,
        prev_jti=jti,
    )

    set_refresh_cookie(response, new_refresh, path=refresh_cookie_path_tenant())
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout")
def tenant_logout(request: Request, response: Response):
    """Logout y revocación de refresh token para tenant (best-effort)."""
    token = request.cookies.get("refresh_token")
    if token:
        best_effort_family_revoke(token)

    delete_auth_cookies(response, path=refresh_cookie_path_tenant())

    if hasattr(request, "state") and hasattr(request.state, "session"):
        request.state.session.clear()
        request.state.session_dirty = True

    return {"ok": True}
