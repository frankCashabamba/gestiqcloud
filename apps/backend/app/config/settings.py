# File: app/config/settings.py
from __future__ import annotations
from functools import lru_cache
from typing import List, Optional, Union, Literal

from uuid import UUID

from pydantic import Field, field_validator, SecretStr,ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración central del backend (Pydantic v2).
    Nota: preferimos validaciones estrictas y defaults seguros.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,             # evita sorpresas con mayúsculas/minúsculas en env
        env_nested_delimiter="__",
    )

   
    # General
    app_name: str = "GestiqCloud"
    debug: bool = False
    ENV: Literal["development", "production"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_VERSION: str = "0.1.0"

    # JWT / Security
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: SecretStr | None = None            # HS*
    JWT_PRIVATE_KEY: SecretStr | None = None           # RS*/ES*
    JWT_PUBLIC_KEY: SecretStr | None = None
    JWT_ADDITIONAL_PUBLIC_KEYS: List[SecretStr] = []   # rotación opcional
    JWT_ISSUER: str = "gestiqcloud"
    JWT_AUDIENCE: Optional[str] = None
    JWT_LEEWAY_SECONDS: int = 30

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SECRET_KEY: SecretStr = SecretStr("change-me")

    # Frontend
    FRONTEND_URL: str
    FRONTEND_MODULES_PATH: Optional[str] = None

    # Cookies / CSRF
    SESSION_COOKIE_NAME: str = "bff_session"
    COOKIE_DOMAIN: Optional[str] = None
    CSRF_COOKIE_NAME: str = "csrf_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:5174"],
        description="Orígenes permitidos (lista o string con comas)."
    )
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = None
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = [
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-CSRF",
        "X-Client-Version",
        "X-Client-Revision",
    ]
    ALLOWED_HOSTS: List[str] = Field(default_factory=list)

    # Base de datos
    DATABASE_URL: SecretStr
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_TIMEOUT: int = 30           # segundos
    DB_STATEMENT_TIMEOUT_MS: int = 15000  # 15s

    # Redis (opcional)
    REDIS_URL: Optional[str] = None

    # CSP / otros headers
    CSP_REPORT_URI: Optional[str] = None
    ALLOW_EMBED: bool = False
    HSTS_ENABLED: bool = True
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=(), payment=()"
    COOP_ENABLED: bool = False
    COEP_ENABLED: bool = False
    CORP_POLICY: str = "same-site"

    TENANT_NAMESPACE_UUID: str = Field(..., description="Namespace para generar tenant UUIDs determinísticos")
    ADMIN_SYSTEM_TENANT_ID: str = Field(
        "00000000-0000-0000-0000-000000000000",
        description="Tenant fijo para admins"
    )

    # Refresh hardening
    REFRESH_ENFORCE_FINGERPRINT: bool = False

    # Legacy API deprecation
    LEGACY_SUNSET: str | None = "Wed, 31 Dec 2025 00:00:00 GMT"
    LEGACY_DEPRECATION_LINK: str | None = "https://docs.example.com/changelog#legacy"

    # Email / SMTP
    EMAIL_HOST: str | None = None
    EMAIL_PORT: int = 587
    EMAIL_USE_TLS: bool = True
    EMAIL_HOST_USER: str | None = None
    EMAIL_HOST_PASSWORD: str | None = None
    DEFAULT_FROM_EMAIL: str = "no-reply@localhost"
    EMAIL_DEV_LOG_ONLY: bool = False

    # Password reset/link base
    PASSWORD_RESET_URL_BASE: str | None = None

    # Uploads / Static user files
    UPLOADS_DIR: str = "uploads"
    UPLOADS_MOUNT_ENABLED: bool = True
    MAX_REQUEST_BYTES: int = 5 * 1024 * 1024
    GZIP_ENABLED: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def split_hosts(cls, v):
        if isinstance(v, str):
            return [h.strip() for h in v.split(",") if h.strip()]
        return v

    @field_validator("FRONTEND_URL")
    @classmethod
    def ensure_frontend_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("FRONTEND_URL debe incluir http(s)://")
        return v

    @field_validator("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD", "DEFAULT_FROM_EMAIL", mode="before")
    @classmethod
    def strip_quotes(cls, v: str | None):
        if isinstance(v, str):
            return v.strip().strip("'").strip('"')
        return v

    @field_validator("EMAIL_PORT", mode="before")
    @classmethod
    def parse_email_port(cls, v):
        if isinstance(v, str):
            s = v.strip().strip("'").strip('"')
            if s.isdigit():
                return int(s)
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def validate_jwt_alg(cls, alg: str) -> str:
        allowed = ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512")
        if alg not in allowed:
            raise ValueError(f"JWT_ALGORITHM inválido: {alg}")
        return alg

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL.get_secret_value()
        return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url

    @property
    def is_prod(self) -> bool:
        return self.ENV == "production"

    def assert_required_for_production(self):
        """Verifica que todas las variables críticas estén definidas en producción."""
        if self.ENV != "production":
            return  # No verificar en desarrollo

        required_vars = [
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "FRONTEND_URL",
            "DATABASE_URL",
            "SESSION_COOKIE_NAME",
            "CSRF_COOKIE_NAME"
        ]

        required_email = [
            "EMAIL_HOST",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "DEFAULT_FROM_EMAIL",
        ]
        required_vars.extend(required_email)

        missing = []
        for var in required_vars:
            value = getattr(self, var, None)
            if isinstance(value, SecretStr):
                if not value.get_secret_value():
                    missing.append(var)
            elif not value:
                missing.append(var)

        # Reglas extra de producción
        if not self.COOKIE_SECURE:
            missing.append("COOKIE_SECURE=True (obligatorio en prod)")
        if self.SECRET_KEY.get_secret_value() == "change-me":
            missing.append("SECRET_KEY (no usar 'change-me' en prod)")
        if self.JWT_ALGORITHM.startswith("HS"):
            if not self.JWT_SECRET_KEY or not self.JWT_SECRET_KEY.get_secret_value():
                missing.append("JWT_SECRET_KEY (HS*)")
        else:
            if not (self.JWT_PRIVATE_KEY and self.JWT_PUBLIC_KEY):
                missing.append("JWT_PRIVATE_KEY/JWT_PUBLIC_KEY (RS*/ES*)")

        if missing:
            raise RuntimeError(
                f"❌ Variables de entorno obligatorias faltantes para producción: {', '.join(missing)}"
            )


# Instancia global de configuración
settings = Settings()
settings.assert_required_for_production()


@lru_cache
def get_settings() -> Settings:
    return settings
