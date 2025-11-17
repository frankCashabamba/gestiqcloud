from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import jwt
from jwt import InvalidTokenError  # re-export usage convenience

try:
    # Prefer app settings when available
    from app.config.settings import settings as app_settings
except Exception:  # pragma: no cover - allow import outside app context
    app_settings = None  # type: ignore


@dataclass
class JwtSettings:
    secret: str
    algorithm: str = "HS256"
    access_ttl_minutes: int = 15
    refresh_ttl_days: int = 7

    @classmethod
    def from_app(cls) -> JwtSettings:
        import logging
        import os

        logger = logging.getLogger(__name__)

        secret: str | None = None
        algo: str = "HS256"
        access_min: int = 15
        refresh_days: int = 7

        # First try environment variables directly (highest priority)
        secret = os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY")

        if secret:
            logger.debug(f"JWT secret loaded from environment variables, secret_len={len(secret)}")

        if not secret and app_settings is not None:
            # Accept both new and existing variable names for compatibility
            s_obj = getattr(app_settings, "JWT_SECRET", None) or getattr(
                app_settings, "JWT_SECRET_KEY", None
            )
            if s_obj is not None and hasattr(s_obj, "get_secret_value"):
                secret = s_obj.get_secret_value()  # pydantic SecretStr
            elif isinstance(s_obj, str):
                secret = s_obj

            # Fallback to SECRET_KEY if available
            if not secret:
                s_key = getattr(app_settings, "SECRET_KEY", None)
                if s_key is not None and hasattr(s_key, "get_secret_value"):
                    secret = s_key.get_secret_value()
                elif isinstance(s_key, str):
                    secret = s_key

            if secret:
                logger.debug(f"JWT secret loaded from app_settings, secret_len={len(secret)}")

            algo = getattr(app_settings, "JWT_ALGORITHM", algo) or algo
            access_min = int(
                getattr(
                    app_settings,
                    "ACCESS_TTL_MINUTES",
                    getattr(app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", access_min),
                )
            )
            refresh_days = int(
                getattr(
                    app_settings,
                    "REFRESH_TTL_DAYS",
                    getattr(app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", refresh_days),
                )
            )

        if not secret:
            # Safe default for tests/dev only
            secret = "devsecretdevsecretdevsecret"
            logger.debug("JWT secret using default devsecret")

        return cls(
            secret=secret,
            algorithm=algo,
            access_ttl_minutes=access_min,
            refresh_ttl_days=refresh_days,
        )


class JwtService:
    def __init__(self, cfg: JwtSettings | None = None):
        self.cfg = cfg or JwtSettings.from_app()
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            f"JwtService created with secret_len={len(self.cfg.secret)}, algorithm={self.cfg.algorithm}"
        )

    def _now(self) -> int:
        import warnings

        from apps.backend.app.shared.utils import now_ts

        warnings.warn(
            "Deprecated: prefer apps.backend.app.shared.utils.now_ts",
            DeprecationWarning,
            stacklevel=2,
        )
        return now_ts()

    def encode(self, payload: Mapping[str, Any], *, kind: str) -> str:
        from app.shared.utils import now_ts

        now = now_ts()
        if kind == "access":
            exp = now + self.cfg.access_ttl_minutes * 60
        elif kind == "refresh":
            exp = now + self.cfg.refresh_ttl_days * 24 * 60 * 60
        else:
            raise ValueError("Unknown token kind")

        claims = {
            **payload,
            "iat": now,
            "nbf": now,
            "exp": exp,
            "type": kind,
        }
        return jwt.encode(claims, self.cfg.secret, algorithm=self.cfg.algorithm)

    def decode(self, token: str, *, expected_kind: str | None = None) -> Mapping[str, Any]:
        import logging

        logger = logging.getLogger(__name__)

        try:
            payload = jwt.decode(token, self.cfg.secret, algorithms=[self.cfg.algorithm])
        except Exception as e:
            logger.error(
                f"JWT decode failed: {type(e).__name__}: {e}, secret_len={len(self.cfg.secret)}, secret_first_10={self.cfg.secret[:10]}, secret_hash={hash(self.cfg.secret)}"
            )
            raise

        if expected_kind is not None:
            tok_kind = payload.get("type") or payload.get("typ") or payload.get("kind")
            logger.debug(f"Token kind validation: expected={expected_kind}, got={tok_kind}")
            if tok_kind != expected_kind:
                logger.error(
                    f"Token kind mismatch: expected={expected_kind}, got={tok_kind}, payload_keys={list(payload.keys())}"
                )
                raise InvalidTokenError("wrong_token_type")
        return payload
