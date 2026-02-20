"""
IDENTITY: Tenant Auth Endpoints
Login, refresh, logout, password change
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.user import User
from app.modules.identity.application.use_cases import (
    ChangePasswordUseCase,
    LoginUseCase,
    LogoutUseCase,
    RefreshTokenUseCase,
)
from app.modules.identity.infrastructure.jwt_service import JwtService
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.identity.infrastructure.rate_limit import SimpleRateLimiter
from app.modules.identity.infrastructure.refresh_repo import SqlRefreshTokenRepo

logger = logging.getLogger(__name__)

# ============================================================================
# INFRASTRUCTURE SINGLETONS
# ============================================================================

_jwt_service = JwtService()
_password_hasher = PasslibPasswordHasher()
_rate_limiter = SimpleRateLimiter()


class _JwtTokenServiceAdapter:
    """Adapts JwtService to the TokenService protocol expected by use cases."""

    def __init__(self, jwt_svc: JwtService):
        self._jwt = jwt_svc

    def issue_access(self, payload: dict) -> str:
        return self._jwt.encode(payload, kind="access")

    def issue_refresh(self, payload: dict, *, jti: str, prev_jti: str | None) -> str:
        full = {**payload, "jti": jti, "prev_jti": prev_jti}
        return self._jwt.encode(full, kind="refresh")

    def decode_and_validate(self, token: str, *, expected_type: str) -> dict:
        return dict(self._jwt.decode(token, expected_kind=expected_type))


_token_service = _JwtTokenServiceAdapter(_jwt_service)


# ============================================================================
# SCHEMAS
# ============================================================================


class LoginRequest(BaseModel):
    """Login request."""

    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    tenant_id: str | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""

    current_password: str = Field(min_length=8, max_length=255)
    new_password: str = Field(min_length=8, max_length=255)


class UserResponse(BaseModel):
    """User info in responses."""

    id: str
    email: str
    name: str | None = None
    is_active: bool


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: UserResponse


class RefreshResponse(BaseModel):
    """Refresh response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/auth",
    tags=["Identity"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Login with email and password. Returns access token + refresh token in HttpOnly cookie."""
    try:
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not user.is_active:
            raise ValueError("Email o contraseña incorrecta")

        refresh_repo = SqlRefreshTokenRepo(db)
        use_case = LoginUseCase(
            token_service=_token_service,
            password_hasher=_password_hasher,
            rate_limiter=_rate_limiter,
            refresh_repo=refresh_repo,
        )

        result = use_case.execute(
            user=user,
            password=payload.password,
            request=request,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "unknown",
            tenant_id=payload.tenant_id,
        )

        response = JSONResponse(
            content={
                "access_token": result["access_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
                "user": result["user"],
            }
        )
        response.set_cookie(
            "refresh_token",
            result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=604800,
            path="/",
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail="Error al iniciar sesión")


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Refresh access token using refresh token from cookie."""
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token in cookie")

        refresh_repo = SqlRefreshTokenRepo(db)
        use_case = RefreshTokenUseCase(
            token_service=_token_service,
            refresh_repo=refresh_repo,
        )

        result = use_case.execute(
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "unknown",
        )

        response = JSONResponse(
            content={
                "access_token": result["access_token"],
                "token_type": result["token_type"],
                "expires_in": result.get("expires_in", 900),
            }
        )
        response.set_cookie(
            "refresh_token",
            result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=604800,
            path="/",
        )
        return response

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception:
        logger.exception("Token refresh exception")
        raise HTTPException(status_code=500, detail="Error al refrescar token")


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Logout: revoke all sessions by revoking refresh token family."""
    try:
        claims = getattr(request.state, "access_claims", {})
        if not claims:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = UUID(claims.get("sub"))
        refresh_token = request.cookies.get("refresh_token")

        refresh_repo = SqlRefreshTokenRepo(db)
        use_case = LogoutUseCase(refresh_repo=refresh_repo)
        use_case.execute(refresh_token=refresh_token, user_id=user_id)

        response = JSONResponse({"message": "Logged out successfully"})
        response.delete_cookie("refresh_token", path="/")
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Logout exception")
        raise HTTPException(status_code=500, detail="Error al cerrar sesión")


@router.post("/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Change user password. Requires current password for verification."""
    try:
        claims = getattr(request.state, "access_claims", {})
        if not claims:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = UUID(claims.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        refresh_repo = SqlRefreshTokenRepo(db)
        use_case = ChangePasswordUseCase(
            password_hasher=_password_hasher,
            refresh_repo=refresh_repo,
        )

        result = use_case.execute(
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            user_id=user_id,
        )

        user.password_hash = result["new_password_hash"]
        user.updated_at = datetime.utcnow()
        db.commit()

        response = JSONResponse({"message": result["message"]})
        response.delete_cookie("refresh_token", path="/")
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Password change exception")
        raise HTTPException(status_code=500, detail="Error al cambiar contraseña")
