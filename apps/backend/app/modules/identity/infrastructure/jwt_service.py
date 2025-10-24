from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping, Optional

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError  # re-export usage convenience

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
    def from_app(cls) -> "JwtSettings":
        secret: Optional[str] = None
        algo: str = "HS256"
        access_min: int = 15
        refresh_days: int = 7

        if app_settings is not None:
            # Accept both new and existing variable names for compatibility
            s_obj = getattr(app_settings, "JWT_SECRET", None) or getattr(app_settings, "JWT_SECRET_KEY", None)
            if s_obj is not None and hasattr(s_obj, "get_secret_value"):
                secret = s_obj.get_secret_value()  # pydantic SecretStr
            elif isinstance(s_obj, str):
                secret = s_obj

            algo = getattr(app_settings, "JWT_ALGORITHM", algo) or algo
            access_min = int(
                getattr(app_settings, "ACCESS_TTL_MINUTES", getattr(app_settings, "ACCESS_TOKEN_EXPIRE_MINUTES", access_min))
            )
            refresh_days = int(
                getattr(app_settings, "REFRESH_TTL_DAYS", getattr(app_settings, "REFRESH_TOKEN_EXPIRE_DAYS", refresh_days))
            )

        if not secret:
            # Safe default for tests/dev only
            secret = "devsecretdevsecretdevsecret"

        return cls(secret=secret, algorithm=algo, access_ttl_minutes=access_min, refresh_ttl_days=refresh_days)


class JwtService:
    def __init__(self, cfg: Optional[JwtSettings] = None):
        self.cfg = cfg or JwtSettings.from_app()

    def _now(self) -> int:
        import warnings
        from apps.backend.app.shared.utils import now_ts
        warnings.warn("Deprecated: prefer apps.backend.app.shared.utils.now_ts", DeprecationWarning, stacklevel=2)
        return now_ts()

    def encode(self, payload: Mapping[str, Any], *, kind: str) -> str:
        from apps.backend.app.shared.utils import now_ts
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

    def decode(self, token: str, *, expected_kind: Optional[str] = None) -> Mapping[str, Any]:
        payload = jwt.decode(token, self.cfg.secret, algorithms=[self.cfg.algorithm])
        if expected_kind is not None:
            tok_kind = payload.get("type") or payload.get("typ") or payload.get("kind")
            if tok_kind != expected_kind:
                raise InvalidTokenError("wrong_token_type")
        return payload
