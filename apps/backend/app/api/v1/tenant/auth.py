 

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.perm_loader import build_tenant_claims
from app.core.i18n import t
from app.core.audit import audit as audit_log
from app.config.database import get_db
from app.core.deps import set_tenant_scope
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.config.settings import settings


from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.identity.infrastructure.rate_limit import SimpleRateLimiter
from app.modules.identity.infrastructure.refresh_repo import SqlRefreshTokenRepo
from app.api.email.email_utils import verificar_token_email

from app.core.auth_http import (
    set_refresh_cookie,
    delete_auth_cookies,
    best_effort_family_revoke,
    refresh_cookie_path_tenant,  # <- IMPORT NECESARIO
)
from app.core.auth_shared import ensure_session, issue_csrf_and_cookie, rotate_refresh

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginTenant(BaseModel):
    identificador: str
    password: str


class SetPasswordIn(BaseModel):
    token: str
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
    rl = limiter.check(request, ident)
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
        limiter.incr_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=None, tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    ok, new_hash = hasher.verify(data.password, user.password_hash)
    if not ok:
        limiter.incr_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=str(user.id), tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # Rehash transparente si procede
    if new_hash:
        user.password_hash = new_hash
        db.add(user)
        db.commit()

    # OK → resetea contador
    limiter.reset(request, ident)

    tenant_id = str(user.empresa.id)
    # UUID para familia de refresh (si el modelo lo tiene); si no, NULL en la tabla
    try:
        tenant_uuid_for_family = str(getattr(user, "tenant_id")) if getattr(user, "tenant_id", None) else None
    except Exception:
        tenant_uuid_for_family = None

    # 3) Sesión + scope
    s = ensure_session(request)
    s.update({"kind": "tenant", "tenant_user_id": str(user.id), "tenant_id": tenant_id})
    request.state.session_dirty = True
    set_tenant_scope(request, tenant_id)

    # 4) CSRF (cookie legible por JS)
    issue_csrf_and_cookie(request, response, path="/")

    # Claims (permisos, tenant, etc.)
    claims = build_tenant_claims(db, user)
    if not claims:
        limiter.incr_fail(request, ident)
        audit_log(db, kind="login_failed", scope="tenant", user_id=str(user.id), tenant_id=None, req=request)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # 5) Refresh family + primer token
    repo = SqlRefreshTokenRepo(db)
    family_id = repo.create_family(user_id=str(user.id), tenant_id=tenant_uuid_for_family)
    jti = repo.issue_token(
        family_id=family_id,
        prev_jti=None,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    # 6) JWTs (devuelven strings)
    access = token_service.issue_access(claims)
    refresh = token_service.issue_refresh(
        {
            "sub": claims["sub"],
            "user_id": claims["user_id"],
            "tenant_id": claims.get("tenant_id"),
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
def tenant_refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    repo = SqlRefreshTokenRepo(db)
    return rotate_refresh(
        request,
        response,
        token_service=token_service,
        repo=repo,
        expected_kind="tenant",
        cookie_path=refresh_cookie_path_tenant(),
    )


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
token_service = PyJWTTokenService()
hasher = PasslibPasswordHasher()
limiter = SimpleRateLimiter()


@router.post("/set-password")
def tenant_set_password(payload: SetPasswordIn, db: Session = Depends(get_db)):
    """Establece nueva contraseña a partir de un token de email válido.

    - El token incluye el email del usuario.
    - Requiere password >= 8 chars (validación básica en FE; reforzamos aquí).
    """
    tok = (payload.token or "").strip()
    new_pwd = (payload.password or "").strip()
    if not tok or not new_pwd:
        raise HTTPException(status_code=400, detail="invalid_request")
    if len(new_pwd) < 8:
        raise HTTPException(status_code=400, detail="weak_password")
    try:
        email = verificar_token_email(tok, max_age=60 * 60 * 24)  # 24h
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_or_expired_token")

    user = db.query(UsuarioEmpresa).filter(func.lower(UsuarioEmpresa.email) == str(email).lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    user.password_hash = hasher.hash(new_pwd)
    # marca como verificado si ese campo existe en el modelo
    try:
        if hasattr(user, "is_verified"):
            setattr(user, "is_verified", True)
    except Exception:
        pass
    db.add(user)
    db.commit()
    return {"ok": True}
