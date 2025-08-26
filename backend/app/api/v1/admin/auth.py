from typing import Mapping
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import verify_password
from app.core.csrf import issue_csrf_token
from app.core.i18n import t
from app.core.audit import audit as audit_log
from app.models.auth.useradmis import SuperUser
from app.core.refresh import (
    family_create,
    token_issue,
    token_mark_used,
    token_is_reused_or_revoked,
    family_revoke,
    token_get_family,
    create_access,
    create_refresh,
    decode_and_validate,
)
from app.config.settings import settings
from app.core.login_rate_limit import check as rl_check, incr_fail as rl_fail, reset as rl_reset
from app.core.auth_http import (
    set_refresh_cookie,
    delete_auth_cookies,
    best_effort_family_revoke,
    refresh_cookie_path_admin,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginAdmin(BaseModel):
    identificador: str
    password: str


admin_tenant_id = settings.ADMIN_SYSTEM_TENANT_ID


@router.post("/login")
def admin_login(
    data: LoginAdmin,
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

    # 1) Lookup (usuario o email, case-insensitive)
    user = (
        db.query(SuperUser)
        .filter(
            or_(
                func.lower(SuperUser.email) == ident,
                func.lower(SuperUser.username) == ident,
            )
        )
        .first()
    )

    # 2) Validación de credenciales (manejar user=None)
    if user is None or not getattr(user, "password_hash", None):
        rl_fail(request, ident)
        audit_log(
            db,
            kind="login",
            scope="admin",
            user_id=None,  # evitar AttributeError si user es None
            tenant_id=admin_tenant_id,
            req=request,
        )
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    ok, new_hash = verify_password(data.password, user.password_hash)
    if not ok:
        rl_fail(request, ident)
        audit_log(
            db,
            kind="login",
            scope="admin",
            user_id=str(user.id),
            tenant_id=admin_tenant_id,
            req=request,
        )
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    if new_hash:
        user.password_hash = new_hash
        db.add(user)
        db.commit()

    # OK → resetea contador
    rl_reset(request, ident)

    # 3) Sesión
    if not hasattr(request, "state") or not hasattr(request.state, "session"):
        request.state.session = {}
    request.state.session.update({"kind": "admin", "admin_user_id": str(user.id)})
    request.state.session_dirty = True

    # 4) CSRF
    csrf = issue_csrf_token(request)
    response.set_cookie("csrf_token", csrf, httponly=False, samesite="lax", secure=not settings.debug)

    # 5) Refresh family + primer token
    family_id = family_create(user_id=str(user.id), tenant_id=admin_tenant_id)
    jti = token_issue(
        family_id,
        prev_jti=None,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    # 6) JWTs
    access = create_access({"sub": user.email, "user_id": str(user.id), "kind": "admin"})
    refresh = create_refresh(
        {"sub": user.email, "user_id": str(user.id), "kind": "admin", "family_id": family_id},
        jti=jti,
        prev_jti=None,
    )

    # 7) Cookie refresh (pasa el string, no .token)
    set_refresh_cookie(response, refresh, path=refresh_cookie_path_admin())

    audit_log(
        db,
        kind="login",
        scope="admin",
        user_id=str(user.id),
        tenant_id=admin_tenant_id,
        req=request,
    )
    return {"access_token": access, "token_type": "bearer", "scope": "admin"}


@router.post("/refresh")
def refresh(request: Request, response: Response):
    """Rotación de refresh token para admin."""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    try:
        payload: Mapping[str, object] = decode_and_validate(token, expected_type="refresh")
    except Exception:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    jti_val = payload.get("jti")
    family_id = token_get_family(jti_val) if isinstance(jti_val, str) else None
    if not family_id:
        fam_payload = payload.get("family_id")
        if isinstance(fam_payload, str):
            family_id = fam_payload

    if not isinstance(jti_val, str) or not family_id:
        raise HTTPException(status_code=401, detail=t(request, "invalid_refresh_token"))

    # Reuse detection
    if token_is_reused_or_revoked(jti_val):
        family_revoke(family_id)
        raise HTTPException(status_code=401, detail=t(request, "compromised_refresh_token"))

    # Rotación
    token_mark_used(jti_val)
    new_jti = token_issue(
        family_id,
        prev_jti=jti_val,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    minimal = {"sub": payload.get("sub"), "user_id": payload.get("user_id")}
    access = create_access({**minimal, "kind": "admin"})
    new_refresh = create_refresh(
        {**minimal, "kind": "admin", "family_id": family_id},
        jti=new_jti,
        prev_jti=jti_val,
    )

    set_refresh_cookie(response, new_refresh, path=refresh_cookie_path_admin())
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout")
def admin_logout(request: Request, response: Response):
    """Logout y revocación de refresh token para admin (best-effort)."""
    token = request.cookies.get("refresh_token")
    if token:
        best_effort_family_revoke(token)

    delete_auth_cookies(response, path=refresh_cookie_path_admin())

    if hasattr(request, "state") and hasattr(request.state, "session"):
        request.state.session.clear()
        request.state.session_dirty = True

    return {"ok": True}


@router.get("/csrf")
def csrf_bootstrap(response: Response, request: Request):
    # Garantiza que exista un contenedor de sesión
    if not hasattr(request, "state") or not hasattr(request.state, "session"):
        request.state.session = {}
    # Genera y guarda en sesión
    token = issue_csrf_token(request)
    # Cookie LEGIBLE por JS (para poder meterla en el header)
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,  # importante para poder leerla en el FE
        samesite="lax",
        path="/",
        secure=not settings.debug,  # en prod con HTTPS → True
    )
    return {"ok": True, "csrfToken": token}
