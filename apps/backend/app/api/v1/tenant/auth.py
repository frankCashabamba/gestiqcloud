import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.email.email_utils import verificar_token_email
from app.config.database import get_db
from app.config.settings import settings
from app.core.audit import audit as audit_log
from app.core.auth_http import refresh_cookie_path_tenant  # <- IMPORT NECESARIO
from app.core.auth_http import delete_auth_cookies, set_access_cookie, set_refresh_cookie
from app.core.auth_shared import ensure_session, issue_csrf_and_cookie, rotate_refresh
from app.core.csrf import issue_csrf_token
from app.core.deps import set_tenant_scope
from app.core.i18n import t
from app.core.jwt_provider import get_token_service as get_shared_token_service
from app.core.perm_loader import build_tenant_claims
from app.models.company.company_user import CompanyUser
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.identity.infrastructure.rate_limit import SimpleRateLimiter
from app.modules.identity.infrastructure.tenant_refresh_repo import TenantSqlRefreshTokenRepo

router = APIRouter(prefix="/auth", tags=["Auth"])
log = logging.getLogger("app.auth.tenant")


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
    try:
        log.info(
            "tenant.login.attempt origin=%s ua=%s ip=%s ident=%s",
            request.headers.get("origin"),
            request.headers.get("user-agent", ""),
            request.client.host if request.client else "",
            ident,
        )
    except Exception:
        pass

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

    # 1) Buscar usuario (case-insensitive) + join con tenant
    user = (
        db.query(CompanyUser)
        .options(joinedload(CompanyUser.tenant))
        .filter(
            or_(
                func.lower(CompanyUser.email) == ident,
                func.lower(CompanyUser.username) == ident,
            )
        )
        .first()
    )

    # 2) Validaciones básicas
    if not user or not user.tenant_id or not user.tenant:
        limiter.incr_fail(request, ident)
        audit_log(
            db,
            kind="login_failed",
            scope="tenant",
            user_id=None,
            tenant_id=None,
            req=request,
        )
        log.warning("tenant.login.invalid_credentials ident=%s", ident)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    ok, new_hash = hasher.verify(data.password, user.password_hash)
    if not ok:
        limiter.incr_fail(request, ident)
        audit_log(
            db,
            kind="login_failed",
            scope="tenant",
            user_id=str(user.id),
            tenant_id=None,
            req=request,
        )
        log.warning("tenant.login.invalid_credentials ident=%s", ident)
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # Rehash transparente si procede
    if new_hash:
        user.password_hash = new_hash
        db.add(user)
        db.commit()

    # OK → resetea contador
    limiter.reset(request, ident)

    # Usar tenant_id directamente (ya es UUID)
    tenant_uuid_for_family = str(user.tenant_id)
    tenant_id = tenant_uuid_for_family

    # 3) Sesión + scope
    s = ensure_session(request)
    s.update({"kind": "tenant", "tenant_user_id": str(user.id), "tenant_id": tenant_id})
    request.state.session_dirty = True
    set_tenant_scope(request, tenant_id)

    # Si resolvimos UUID de tenant, propágalo a la sesión DB (GUC + session.info)
    try:
        if tenant_uuid_for_family:
            from sqlalchemy import text as _text

            db.execute(
                _text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(tenant_uuid_for_family)},
            )
            try:
                db.info["tenant_id"] = str(tenant_uuid_for_family)
            except Exception:
                pass
    except Exception:
        # No bloquear el login por fallos al fijar el GUC
        pass

    # 4) CSRF (cookie legible por JS)
    issue_csrf_and_cookie(request, response, path="/")

    # Claims (permisos, tenant, etc.)
    # Asegura que la sesión no esté en estado aborted por alguna consulta previa
    try:
        from sqlalchemy import text as _text

        db.execute(_text("SELECT 1"))
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
    try:
        claims = build_tenant_claims(db, user)
    except Exception:
        # Log del error real que está abortando la transacción
        try:
            log.exception(
                "tenant.login.claims_error usuario_id=%s tenant_id=%s",
                str(getattr(user, "id", None)),
                str(getattr(user, "tenant_id", None)),
            )
        except Exception:
            pass
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="claims_error")
    if not claims:
        limiter.incr_fail(request, ident)
        audit_log(
            db,
            kind="login_failed",
            scope="tenant",
            user_id=str(user.id),
            tenant_id=None,
            req=request,
        )
        raise HTTPException(status_code=401, detail=t(request, "invalid_credentials"))

    # 5) Refresh family + primer token
    repo = TenantSqlRefreshTokenRepo(db)
    try:
        family_id = repo.create_family(user_id=str(user.id), tenant_id=tenant_uuid_for_family)
        jti = repo.issue_token(
            family_id=family_id,
            prev_jti=None,
            user_agent=request.headers.get("user-agent", ""),
            ip=request.client.host if request.client else "",
        )
    except Exception:
        # Log del error raíz al crear familia/emitir token
        try:
            log.exception(
                "tenant.login.refresh_family_error usuario_id=%s tenant_uuid=%s",
                str(getattr(user, "id", None)),
                tenant_uuid_for_family,
            )
        except Exception:
            pass
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="refresh_family_error")

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
    # Access token en cookie Lax (además del body)
    try:
        set_access_cookie(response, access, path="/")
    except Exception:
        pass

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
        "is_company_admin": claims.get("is_company_admin"),
    }


@router.post("/refresh")
def tenant_refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    repo = TenantSqlRefreshTokenRepo(db)
    try:
        log.debug(
            "tenant.refresh.attempt ua=%s ip=%s",
            request.headers.get("user-agent", ""),
            request.client.host if request.client else "",
        )
    except Exception:
        pass
    res = rotate_refresh(
        request,
        response,
        token_service=token_service,
        repo=repo,
        expected_kind="tenant",
        cookie_path=refresh_cookie_path_tenant(),
    )
    try:
        log.debug("tenant.refresh.ok")
    except Exception:
        pass
    return res


@router.get("/csrf")
def tenant_csrf_bootstrap(response: Response, request: Request):
    """Entrega un token CSRF y lo persiste en cookie legible por el FE."""
    if not hasattr(request, "state") or not hasattr(request.state, "session"):
        request.state.session = {}
    token = issue_csrf_token(request)
    response.set_cookie(
        key="csrf_token",
        value=token,
        httponly=False,
        samesite="lax",
        path="/",
        secure=not settings.debug,
    )
    return {"ok": True, "csrfToken": token}


@router.post("/logout")
def tenant_logout(request: Request, response: Response):
    """Logout y revocación de refresh token para tenant (best-effort)."""
    token = request.cookies.get("refresh_token")
    if token:
        try:
            _best_effort_tenant_family_revoke(token)
        except Exception:
            pass

    delete_auth_cookies(response, path=refresh_cookie_path_tenant())

    if hasattr(request, "state") and hasattr(request.state, "session"):
        request.state.session.clear()
        request.state.session_dirty = True

    return {"ok": True}


def _best_effort_tenant_family_revoke(refresh_token: str) -> None:
    """
    Revoca la familia referida por un refresh token de tenant (tablas tenant_refresh_*).
    No lanza.
    """
    try:
        from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
        from app.config.database import SessionLocal

        payload = PyJWTTokenService().decode_and_validate(refresh_token, expected_type="refresh")
        jti = payload.get("jti")
        if not isinstance(jti, str) or not jti:
            return
        with SessionLocal() as db:
            fam = TenantSqlRefreshTokenRepo(db).get_family(jti=jti)
            if fam:
                TenantSqlRefreshTokenRepo(db).revoke_family(family_id=fam)
    except Exception:
        pass


token_service = get_shared_token_service()
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

    user = db.query(CompanyUser).filter(func.lower(CompanyUser.email) == str(email).lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")

    user.password_hash = hasher.hash(new_pwd)
    # marca como verificado si ese campo existe en el modelo
    try:
        if hasattr(user, "is_verified"):
            user.is_verified = True
    except Exception:
        pass
    db.add(user)
    db.commit()
    return {"ok": True}
