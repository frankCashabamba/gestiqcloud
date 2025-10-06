# app/core/auth_http.py
from typing import Optional, Mapping
from fastapi import Response
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.modules.identity.infrastructure.refresh_repo import SqlRefreshTokenRepo
from app.config.database import SessionLocal

# --- Cookie PATHS (alineados con app.main) ---
# Admin router:   main prefix "/api/v1"  + router prefix "/auth"   => /api/v1/auth
# Tenant router:  main prefix "/api/v1/tenant" + router "/auth"    => /api/v1/tenant/auth
ADMIN_REFRESH_COOKIE_PATH = "/api/v1/admin/auth"
TENANT_REFRESH_COOKIE_PATH = "/api/v1/tenant/auth"

# ---- Cookies ----

def cookie_domain() -> Optional[str]:
    """Dominio para cookies según entorno (None en dev)."""
    try:
        from app.config.settings import settings
        return settings.COOKIE_DOMAIN if settings.ENV == "production" else None
    except Exception:
        return None

def refresh_cookie_path_admin() -> str:
    return ADMIN_REFRESH_COOKIE_PATH

def refresh_cookie_path_tenant() -> str:
    return TENANT_REFRESH_COOKIE_PATH

def refresh_cookie_kwargs(*, path: str) -> dict:
    """Atributos estándar para la cookie de refresh."""
    try:
        from app.config.settings import settings
        # Prefer explicit cookie settings when provided
        secure = bool(getattr(settings, "COOKIE_SECURE", (settings.ENV == "production")))
        samesite = getattr(settings, "COOKIE_SAMESITE", "lax") or ("strict" if settings.ENV == "production" else "lax")
    except Exception:
        secure = False
        samesite = "lax"
    return dict(
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=path,
        domain=cookie_domain(),
    )

def set_refresh_cookie(response: Response, token_str: str, *, path: str) -> None:
    response.set_cookie("refresh_token", token_str, **refresh_cookie_kwargs(path=path))

def delete_auth_cookies(response: Response, *, path: str) -> None:
    """Borra refresh y CSRF usando mismos atributos que al setear."""
    response.delete_cookie("refresh_token", path=path, domain=cookie_domain())
    # Si usas CSRF cookie legible por JS en '/', bórrala ahí también
    response.delete_cookie("csrf_token", path="/", domain=cookie_domain())

# ---- Family helpers ----

def extract_family_id_from_refresh(token: str) -> Optional[str]:
    """Best-effort para obtener family_id desde el refresh token."""
    try:
        payload: Mapping[str, object] = PyJWTTokenService().decode_and_validate(token, expected_type="refresh")
        jti = payload.get("jti")
        fam_payload = payload.get("family_id")
        if isinstance(jti, str) and jti:
            # lookup in DB
            with SessionLocal() as db:
                fam_from_db = SqlRefreshTokenRepo(db).get_family(jti=jti)
            if fam_from_db:
                return fam_from_db
        if isinstance(fam_payload, str) and fam_payload:
            return fam_payload
    except Exception:
        pass
    return None

def best_effort_family_revoke(refresh_token: str) -> None:
    """Revoca la familia referida por un refresh token si es posible (no lanza)."""
    try:
        fam = extract_family_id_from_refresh(refresh_token)
        if fam:
            try:
                with SessionLocal() as db:
                    SqlRefreshTokenRepo(db).revoke_family(family_id=fam)
            except Exception:
                pass
    except Exception:
        pass
