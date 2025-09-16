from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.i18n import t
from app.core.audit import audit as audit_log
from app.models.auth.useradmis import SuperUser
from app.config.settings import settings
from app.core.auth_http import (
    set_refresh_cookie,
    delete_auth_cookies,
    best_effort_family_revoke,
    refresh_cookie_path_admin,
)
from app.core.auth_shared import ensure_session, issue_csrf_and_cookie, rotate_refresh

# Identity services (ports/adapters)
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.identity.infrastructure.rate_limit import SimpleRateLimiter
from app.modules.identity.infrastructure.refresh_repo import SqlRefreshTokenRepo
from app.core.csrf import issue_csrf_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginAdmin(BaseModel):
    identificador: str
    password: str


admin_tenant_id = settings.ADMIN_SYSTEM_TENANT_ID

# Service instances (simple DI for now)
token_service = PyJWTTokenService()
hasher = PasslibPasswordHasher()
limiter = SimpleRateLimiter()


@router.post("/login")
def admin_login(
    data: LoginAdmin,
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
        limiter.incr_fail(request, ident)
        audit_log(
            db,
            kind="login",
            scope="admin",
            user_id=None,  # evitar AttributeError si user es None
            tenant_id=admin_tenant_id,
            req=request,
        )
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    ok, new_hash = hasher.verify(data.password, user.password_hash)
    if not ok:
        limiter.incr_fail(request, ident)
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
    limiter.reset(request, ident)

    # 3) Sesión + CSRF
    s = ensure_session(request)
    s.update({"kind": "admin", "admin_user_id": str(user.id)})
    request.state.session_dirty = True
    issue_csrf_and_cookie(request, response, path="/")

    # 5) Refresh family + primer token
    repo = SqlRefreshTokenRepo(db)
    family_id = repo.create_family(user_id=str(user.id), tenant_id=admin_tenant_id)
    jti = repo.issue_token(
        family_id=family_id,
        prev_jti=None,
        user_agent=request.headers.get("user-agent", ""),
        ip=request.client.host if request.client else "",
    )

    # 6) JWTs
    access = token_service.issue_access({"sub": user.email, "user_id": str(user.id), "kind": "admin"})
    refresh = token_service.issue_refresh(
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
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    """Rotación de refresh token para admin (unificado)."""
    repo = SqlRefreshTokenRepo(db)
    return rotate_refresh(
        request,
        response,
        token_service=token_service,
        repo=repo,
        expected_kind="admin",
        cookie_path=refresh_cookie_path_admin(),
    )


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
