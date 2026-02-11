"""
Utilidades para manejo de JWT en cookies HttpOnly.
Migración desde localStorage (frontend) a cookies seguras.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel

from app.config.settings import settings


class TokenCookieConfig(BaseModel):
    """Configuración de cookies para tokens JWT"""

    # Nombres de cookies
    ACCESS_TOKEN_COOKIE: str = "access_token"
    REFRESH_TOKEN_COOKIE: str = "refresh_token"

    # Tiempos de expiración
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Flags de seguridad
    HTTPONLY: bool = True
    SECURE: bool = True  # Solo HTTPS (prod)
    SAMESITE: str = "lax"  # Previene CSRF
    DOMAIN: str | None = None
    PATH: str = "/"


def set_access_token_cookie(
    response: Response, token: str, expires_delta: timedelta | None = None
) -> None:
    """
    Establece cookie HttpOnly con access token.

    Args:
        response: FastAPI Response object
        token: JWT token string
        expires_delta: Tiempo de expiración (default: 60 min)
    """
    config = TokenCookieConfig()

    if expires_delta is None:
        expires_delta = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Calcular tiempo de expiración
    expires = datetime.now(UTC) + expires_delta

    response.set_cookie(
        key=config.ACCESS_TOKEN_COOKIE,
        value=token,
        max_age=int(expires_delta.total_seconds()),
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        path=config.PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,  # True en prod
        httponly=config.HTTPONLY,  # No accesible desde JS
        samesite=config.SAMESITE,  # Previene CSRF
    )


def set_refresh_token_cookie(
    response: Response, token: str, expires_delta: timedelta | None = None
) -> None:
    """
    Establece cookie HttpOnly con refresh token.

    Args:
        response: FastAPI Response object
        token: JWT refresh token string
        expires_delta: Tiempo de expiración (default: 30 días)
    """
    config = TokenCookieConfig()

    if expires_delta is None:
        expires_delta = timedelta(days=config.REFRESH_TOKEN_EXPIRE_DAYS)

    expires = datetime.now(UTC) + expires_delta

    response.set_cookie(
        key=config.REFRESH_TOKEN_COOKIE,
        value=token,
        max_age=int(expires_delta.total_seconds()),
        expires=expires.strftime("%a, %d %b %Y %H:%M:%S GMT"),
        path=config.PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=config.HTTPONLY,
        samesite=config.SAMESITE,
    )


def get_token_from_cookie(request: Request) -> str | None:
    """
    Extrae access token desde cookie.

    Args:
        request: FastAPI Request object

    Returns:
        Token string o None si no existe
    """
    config = TokenCookieConfig()
    return request.cookies.get(config.ACCESS_TOKEN_COOKIE)


def get_refresh_token_from_cookie(request: Request) -> str | None:
    """
    Extrae refresh token desde cookie.

    Args:
        request: FastAPI Request object

    Returns:
        Refresh token string o None si no existe
    """
    config = TokenCookieConfig()
    return request.cookies.get(config.REFRESH_TOKEN_COOKIE)


def clear_auth_cookies(response: Response) -> None:
    """
    Elimina todas las cookies de autenticación (logout).

    Args:
        response: FastAPI Response object
    """
    config = TokenCookieConfig()

    # Eliminar access token
    response.delete_cookie(
        key=config.ACCESS_TOKEN_COOKIE,
        path=config.PATH,
        domain=settings.COOKIE_DOMAIN,
    )

    # Eliminar refresh token
    response.delete_cookie(
        key=config.REFRESH_TOKEN_COOKIE,
        path=config.PATH,
        domain=settings.COOKIE_DOMAIN,
    )


def require_token_from_cookie(request: Request) -> str:
    """
    Requiere access token desde cookie (lanza HTTPException si no existe).

    Args:
        request: FastAPI Request object

    Returns:
        Token string

    Raises:
        HTTPException 401 si no hay token
    """
    token = get_token_from_cookie(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Token missing from cookie.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


# Migración gradual: Soportar header Y cookie
def get_token_from_cookie_or_header(request: Request) -> str | None:
    """
    Obtiene token desde cookie (preferido) o Authorization header (legacy).

    Útil para migración gradual desde localStorage a cookies.

    Args:
        request: FastAPI Request object

    Returns:
        Token string o None
    """
    # 1. Intentar desde cookie (preferido)
    token = get_token_from_cookie(request)
    if token:
        return token

    # 2. Fallback a header Authorization (legacy)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "").strip()

    return None
