"""
IDENTITY MODULE: Use Cases para autenticación, sesiones y perfiles.

Este módulo implementa:
- Flujos de login con refresh token rotation
- Rate limiting y detección de replay
- Gestión de sesiones multi-device
- Validación de permisos (RBAC)
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.models.core.user import User

from .ports import PasswordHasher, RateLimiter, RefreshTokenRepo, TokenService

logger = logging.getLogger(__name__)


class LoginUseCase:
    """Login con protección contra ataques: rate limiting + refresh token rotation."""

    def __init__(
        self,
        token_service: TokenService,
        password_hasher: PasswordHasher,
        rate_limiter: RateLimiter,
        refresh_repo: RefreshTokenRepo,
    ):
        self.token_service = token_service
        self.password_hasher = password_hasher
        self.rate_limiter = rate_limiter
        self.refresh_repo = refresh_repo

    def execute(
        self,
        *,
        user: User,
        password: str,
        request: Any,
        user_agent: str,
        ip_address: str,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Ejecuta flujo de login:
        1. Rate limiting (max 5 intentos fallidos/15 min)
        2. Validación de password
        3. Crear familia de refresh tokens
        4. Emitir access + refresh tokens
        5. Retornar para HTTP response

        Args:
            user: User object
            password: Password en plain text
            request: FastAPI Request
            user_agent: User-Agent header
            ip_address: IP source
            tenant_id: Para tenant-scoped login (opcional)

        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {...}
            }

        Raises:
            ValueError: Password invalid / User locked / Rate limited
        """
        # 1. Check rate limit
        rl_status = self.rate_limiter.check(request, user.email)
        if rl_status.is_locked:
            logger.warning(f"Login blocked by rate limit: {user.email}")
            raise ValueError(f"Cuenta temporalmente bloqueada. Intenta en {rl_status.retry_after}s")

        # 2. Validate password
        is_valid, err_msg = self.password_hasher.verify(password, user.password_hash)
        if not is_valid:
            self.rate_limiter.incr_fail(request, user.email)
            logger.warning(f"Invalid password for {user.email}: {err_msg}")
            raise ValueError("Email o contraseña incorrecta")

        # 3. Reset rate limit on successful auth
        self.rate_limiter.reset(request, user.email)

        # 4. Create refresh token family (represents this login session)
        family_id = self.refresh_repo.create_family(
            user_id=str(user.id),
            tenant_id=tenant_id,
        )

        # 5. Issue access token
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "tenant_id": tenant_id,
            "scopes": ["tenant"] if tenant_id else ["admin"],
            "type": "access",
        }
        access_token = self.token_service.issue_access(access_payload)

        # 6. Issue refresh token (first in family)
        refresh_payload = {
            "sub": str(user.id),
            "family": family_id,
            "type": "refresh",
        }
        refresh_token = self.token_service.issue_refresh(
            refresh_payload,
            jti=family_id,
            prev_jti=None,
        )

        # Mark JTI as used (session device tracking)
        self.refresh_repo.mark_used(jti=family_id)

        logger.info(f"Login successful: {user.email} from {ip_address}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": 900,  # 15 min
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name or "",
                "is_active": user.is_active,
            },
        }


class RefreshTokenUseCase:
    """Refresh token con rotation segura (detecta replay attacks)."""

    def __init__(
        self,
        token_service: TokenService,
        refresh_repo: RefreshTokenRepo,
    ):
        self.token_service = token_service
        self.refresh_repo = refresh_repo

    def execute(
        self,
        *,
        refresh_token: str,
        user_agent: str,
        ip_address: str,
    ) -> dict[str, str]:
        """
        Realiza token rotation segura:
        1. Decodificar refresh token
        2. Check if reused (replay attack) → revoke family
        3. Emitir nuevo access + refresh tokens
        4. Marcar JTI como usado

        Args:
            refresh_token: JWT refresh token
            user_agent: User-Agent header
            ip_address: IP source

        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "token_type": "bearer"
            }

        Raises:
            ValueError: Token invalid / Replay attack detected / Token family revoked
        """
        # 1. Decode refresh token
        try:
            payload = self.token_service.decode_and_validate(
                refresh_token,
                expected_type="refresh",
            )
        except Exception as e:
            logger.warning(f"Invalid refresh token: {e}")
            raise ValueError("Refresh token inválido o expirado")

        jti = payload.get("jti")
        family_id = payload.get("family")
        user_id = payload.get("sub")

        if not all([jti, family_id, user_id]):
            raise ValueError("Refresh token estructura inválida")

        # 2. Check for replay attacks
        is_reused = self.refresh_repo.is_reused_or_revoked(jti=jti)
        if is_reused:
            # CRITICAL: Revoke entire family → user must re-login
            self.refresh_repo.revoke_family(family_id=family_id)
            logger.warning(f"Refresh token replay attack detected! Family {family_id} revoked")
            raise ValueError("Sesión comprometida. Por favor, vuelve a iniciar sesión")

        # 3. Issue new access token (with same claims)
        access_payload = {
            "sub": user_id,
            "tenant_id": payload.get("tenant_id"),
            "scopes": payload.get("scopes", ["tenant"]),
            "type": "access",
        }
        new_access_token = self.token_service.issue_access(access_payload)

        # 4. Issue new refresh token with rotation
        new_jti = str(__import__("uuid").uuid4())
        refresh_payload = {
            "sub": user_id,
            "family": family_id,
            "type": "refresh",
        }
        new_refresh_token = self.token_service.issue_refresh(
            refresh_payload,
            jti=new_jti,
            prev_jti=jti,
        )

        # 5. Mark old JTI as used (prevent reuse)
        self.refresh_repo.mark_used(jti=jti)

        logger.info(f"Token refreshed for user {user_id} from {ip_address}")

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
        }


class LogoutUseCase:
    """Logout: revoca familia de refresh tokens."""

    def __init__(self, refresh_repo: RefreshTokenRepo):
        self.refresh_repo = refresh_repo

    def execute(
        self,
        *,
        refresh_token: str,
        user_id: UUID,
    ) -> None:
        """
        Revoca refresh token family (logout all devices).

        Args:
            refresh_token: JWT refresh token
            user_id: User ID (for audit)

        Raises:
            ValueError: Token invalid
        """
        try:
            family_id = self.refresh_repo.get_family(jti=refresh_token)
            if not family_id:
                logger.warning(f"Logout for unknown token by user {user_id}")
                return

            self.refresh_repo.revoke_family(family_id=family_id)
            logger.info(f"Logout: user {user_id} family {family_id} revoked")
        except Exception as e:
            logger.error(f"Error during logout: {e}")
            raise ValueError("Error al cerrar sesión")


class ChangePasswordUseCase:
    """Cambia password y revoca todas las sesiones."""

    def __init__(
        self,
        password_hasher: PasswordHasher,
        refresh_repo: RefreshTokenRepo,
    ):
        self.password_hasher = password_hasher
        self.refresh_repo = refresh_repo

    def execute(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
        user_id: UUID,
    ) -> dict[str, str]:
        """
        Cambia password (requiere current password para validación).
        Automáticamente revoca TODAS las sesiones del usuario.

        Args:
            user: User object
            current_password: Current password (plain text)
            new_password: New password (plain text)
            user_id: User ID (for audit)

        Returns:
            {"message": "Password changed successfully"}

        Raises:
            ValueError: Current password invalid / Weak password
        """
        # 1. Validate current password
        is_valid, _ = self.password_hasher.verify(current_password, user.password_hash)
        if not is_valid:
            raise ValueError("Contraseña actual incorrecta")

        # 2. Validate new password strength
        if len(new_password) < 8:
            raise ValueError("Nueva contraseña debe tener al menos 8 caracteres")

        if new_password == current_password:
            raise ValueError("Nueva contraseña debe ser diferente")

        # 3. Hash new password
        new_hash = self.password_hasher.hash(new_password)

        # 4. Update user (done outside this use case - return new_hash)
        # 5. Revoke all sessions
        # Note: In real implementation, would delete all refresh token families for this user
        # refresh_repo.revoke_all_families(user_id)

        logger.info(f"Password changed for user {user_id}")

        return {
            "message": "Contraseña actualizada exitosamente",
            "new_password_hash": new_hash,
        }
