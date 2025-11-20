# app/core/jwt_provider.py
"""
Centralized JWT token service provider.
Ensures a single, consistent instance is used throughout the application
to avoid secret key mismatches between token generation and validation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

logger = logging.getLogger(__name__)

_token_service_instance: PyJWTTokenService | None = None


def get_token_service() -> PyJWTTokenService:
    """Get or create the singleton token service instance."""
    global _token_service_instance
    if _token_service_instance is None:
        from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

        _token_service_instance = PyJWTTokenService()
        logger.debug(f"Created new token service instance: {id(_token_service_instance)}")
    else:
        logger.debug(f"Returning existing token service instance: {id(_token_service_instance)}")
    return _token_service_instance


def reset_token_service() -> None:
    """Reset the token service instance (mainly for testing)."""
    global _token_service_instance
    _token_service_instance = None
