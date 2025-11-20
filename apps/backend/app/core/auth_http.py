from collections.abc import Mapping

from fastapi import Response

from app.config.database import SessionLocal
from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService
from app.modules.identity.infrastructure.refresh_repo import SqlRefreshTokenRepo

# Cookie paths (alineados con app.main)
ADMIN_REFRESH_COOKIE_PATH = "/api/v1/admin/auth"
TENANT_REFRESH_COOKIE_PATH = "/api/v1/tenant/auth"


def cookie_domain() -> str | None:
    """Dominio para cookies segun entorno (None en dev)."""
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
    """Atributos estandar para la cookie de refresh (normaliza SameSite)."""
    try:
        from app.config.settings import settings

        secure = bool(getattr(settings, "COOKIE_SECURE", (settings.ENV == "production")))
        raw = getattr(settings, "COOKIE_SAMESITE", "lax") or (
            "strict" if settings.ENV == "production" else "lax"
        )
    except Exception:
        secure = False
        raw = "lax"
    low = str(raw).strip().lower()
    samesite = "Lax"
    if low == "none":
        samesite = "None"
    elif low == "strict":
        samesite = "Strict"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": samesite,
        "path": path,
        "domain": cookie_domain(),
    }


def set_refresh_cookie(response: Response, token_str: str, *, path: str) -> None:
    response.set_cookie("refresh_token", token_str, **refresh_cookie_kwargs(path=path))


def set_access_cookie(response: Response, token_str: str, *, path: str = "/") -> None:
    """Setea access_token en cookie HttpOnly con SameSite=Lax (solo navegacion propia)."""
    try:
        from app.config.settings import settings

        secure = bool(getattr(settings, "COOKIE_SECURE", (settings.ENV == "production")))
    except Exception:
        secure = False
    response.set_cookie(
        key="access_token",
        value=token_str,
        httponly=True,
        samesite="Lax",
        secure=secure,
        path=path,
        domain=cookie_domain(),
    )


def delete_auth_cookies(response: Response, *, path: str) -> None:
    """Borra refresh y CSRF usando mismos atributos que al setear."""
    response.delete_cookie("refresh_token", path=path, domain=cookie_domain())
    response.delete_cookie("access_token", path="/", domain=cookie_domain())
    response.delete_cookie("csrf_token", path="/", domain=cookie_domain())


def extract_family_id_from_refresh(token: str) -> str | None:
    """Best-effort para obtener family_id desde el refresh token."""
    try:
        payload: Mapping[str, object] = PyJWTTokenService().decode_and_validate(
            token, expected_type="refresh"
        )
        jti = payload.get("jti")
        fam_payload = payload.get("family_id")
        if isinstance(jti, str) and jti:
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
