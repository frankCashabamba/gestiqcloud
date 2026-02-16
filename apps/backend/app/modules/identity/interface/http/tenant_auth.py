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

logger = logging.getLogger(__name__)

# ============================================================================
# SCHEMAS
# ============================================================================


class LoginRequest(BaseModel):
    """Login request."""

    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=255)
    tenant_id: str | None = None  # Optional for tenant-scoped login


class RefreshRequest(BaseModel):
    """Refresh token request (from cookie)."""

    pass  # Refresh token comes from HttpOnly cookie


class LogoutRequest(BaseModel):
    """Logout request."""

    pass


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
) -> dict:
    """
    Login with email and password.

    Returns access token + refresh token in HttpOnly cookie.

    Args:
        payload: LoginRequest with email, password
        request: FastAPI request
        db: Database session

    Returns:
        LoginResponse with access_token + user info

    Raises:
        HTTPException 400: Invalid credentials
        HTTPException 429: Rate limit exceeded
    """
    try:
        # Get user by email
        user = db.query(User).filter(User.email == payload.email).first()
        if not user or not user.is_active:
            logger.warning(f"Login failed: user not found or inactive: {payload.email}")
            raise ValueError("Email o contraseña incorrecta")

        # Use case execution (will validate password, rate limit, etc)
        # For now, just return success
        # TODO: Wire in actual use case dependencies
        use_case = LoginUseCase(
            token_service=None,  # TODO: inject
            password_hasher=None,  # TODO: inject
            rate_limiter=None,  # TODO: inject
            refresh_repo=None,  # TODO: inject
        )

        result = use_case.execute(
            user=user,
            password=payload.password,
            request=request,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "0.0.0.0",
            tenant_id=payload.tenant_id,
        )

        # Build response with cookie
        response = JSONResponse(
            content={
                "access_token": result["access_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
                "user": result["user"],
            }
        )

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            "refresh_token",
            result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=604800,  # 7 days
            path="/",
        )

        logger.info(f"Login successful for user {user.email}")
        return response

    except ValueError as e:
        logger.warning(f"Login validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Login error")
        raise HTTPException(status_code=500, detail="Error al iniciar sesión")


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token from cookie.

    Implements token rotation: old refresh → new access + new refresh.

    Args:
        request: FastAPI request (contains refresh_token cookie)
        db: Database session

    Returns:
        RefreshResponse with new access_token

    Raises:
        HTTPException 401: No/invalid refresh token
        HTTPException 401: Token replay attack detected
    """
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token in cookie")

        # Use case
        use_case = RefreshTokenUseCase(
            token_service=None,  # TODO: inject
            refresh_repo=None,  # TODO: inject
        )

        result = use_case.execute(
            refresh_token=refresh_token,
            user_agent=request.headers.get("user-agent", "unknown"),
            ip_address=request.client.host if request.client else "0.0.0.0",
        )

        # Update cookie with new refresh token
        response = JSONResponse(
            content={
                "access_token": result["access_token"],
                "token_type": result["token_type"],
                "expires_in": result["expires_in"],
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

        logger.debug("Token refreshed successfully")
        return response

    except ValueError as e:
        logger.warning(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.exception("Token refresh exception")
        raise HTTPException(status_code=500, detail="Error al refrescar token")


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Logout: revoke all sessions by revoking refresh token family.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException 401: Not authenticated
    """
    try:
        # Get user from claims
        claims = getattr(request.state, "access_claims", {})
        if not claims:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = UUID(claims.get("sub"))
        refresh_token = request.cookies.get("refresh_token")

        # Use case
        use_case = LogoutUseCase(
            refresh_repo=None,  # TODO: inject
        )

        use_case.execute(refresh_token=refresh_token, user_id=user_id)

        # Clear cookie
        response = JSONResponse({"message": "Logged out successfully"})
        response.delete_cookie("refresh_token", path="/")

        logger.info(f"Logout for user {user_id}")
        return response

    except ValueError as e:
        logger.warning(f"Logout error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Logout exception")
        raise HTTPException(status_code=500, detail="Error al cerrar sesión")


@router.post("/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """
    Change user password.

    Requires current password for verification.
    Revokes all sessions after password change.

    Args:
        payload: ChangePasswordRequest
        request: FastAPI request
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException 400: Current password invalid / Weak password
        HTTPException 401: Not authenticated
    """
    try:
        # Get user
        claims = getattr(request.state, "access_claims", {})
        if not claims:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = UUID(claims.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        # Use case
        use_case = ChangePasswordUseCase(
            password_hasher=None,  # TODO: inject
            refresh_repo=None,  # TODO: inject
        )

        result = use_case.execute(
            user=user,
            current_password=payload.current_password,
            new_password=payload.new_password,
            user_id=user_id,
        )

        # Update user password
        user.password_hash = result["new_password_hash"]
        user.updated_at = datetime.utcnow()
        db.commit()

        # Clear all sessions
        response = JSONResponse(result)
        response.delete_cookie("refresh_token", path="/")

        logger.info(f"Password changed for user {user_id}")
        return response

    except ValueError as e:
        logger.warning(f"Password change validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Password change exception")
        raise HTTPException(status_code=500, detail="Error al cambiar contraseña")
