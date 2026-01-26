# File: app/config/settings.py
from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# UNIFIED env loading (replaces _load_env and _load_env_all)
from app.config.env_loader import get_env_file_path, load_env_file, inject_env_variables

# Load unified .env file (single source of truth)
_ENV_FILE = get_env_file_path()
_ENV_VARS = load_env_file(_ENV_FILE)
inject_env_variables(_ENV_VARS)
os.environ.setdefault("ENV_FILE_USED", str(_ENV_FILE.resolve()))


def _log_env_info():
    """Log environment info for debugging"""
    try:
        env = os.getenv("ENVIRONMENT", "development")
        used = os.getenv("ENV_FILE_USED")
        has_secret = bool(os.getenv("SECRET_KEY"))
        print(
            f"[settings] ENVIRONMENT={env} ENV_FILE={used} SECRET_KEY_PRESENT={has_secret}"
        )
    except Exception:
        pass


_log_env_info()
_ENV_FILE_PATH = Path(os.getenv("ENV_FILE_USED")).resolve() if os.getenv("ENV_FILE_USED") else None


def _ensure_dev_secret():
    try:
        env = os.getenv("ENV", "development").lower()
        if env != "production" and not os.getenv("SECRET_KEY"):
            import secrets

            os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
            os.environ.setdefault("SECRET_KEY_AUTO", "true")
            used = os.getenv("ENV_FILE_USED") or "<none>"
            print(
                "[settings][WARNING] Generated temporary SECRET_KEY for development;",
                "ENV_FILE_USED=",
                used,
            )
    except Exception:
        pass


_ensure_dev_secret()


class Settings(BaseSettings):
    """
    Configuración central del backend (Pydantic v2).
    Nota: preferimos validaciones estrictas y defaults seguros.
    """

    model_config = SettingsConfigDict(
        env_file=(str(_ENV_FILE_PATH) if _ENV_FILE_PATH else ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,  # evita sorpresas con mayúsculas/minúsculas en env
        env_nested_delimiter="__",
    )

    # General
    app_name: str = "GestiqCloud"
    debug: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment: development, staging, or production"
    )
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_VERSION: str = "0.1.0"

    # JWT / Security
    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: SecretStr | None = None  # HS*
    JWT_PRIVATE_KEY: SecretStr | None = None  # RS*/ES*
    JWT_PUBLIC_KEY: SecretStr | None = None
    JWT_ADDITIONAL_PUBLIC_KEYS: list[SecretStr] = []  # rotación opcional
    JWT_ISSUER: str = "gestiqcloud"
    JWT_AUDIENCE: str | None = None
    JWT_LEEWAY_SECONDS: int = 30

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    SECRET_KEY: SecretStr = Field(..., json_schema_extra={"env": "SECRET_KEY"})

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """Valida que SECRET_KEY sea seguro en todos los entornos"""
        val = v.get_secret_value()
        if val == "change-me":
            raise ValueError(
                "SECRET_KEY no puede ser 'change-me'. Genera una clave segura de ≥32 caracteres."
            )
        if len(val) < 32:
            env = os.getenv("ENV", "development").lower()
            if env != "production":
                derived = hashlib.sha256(val.encode("utf-8")).hexdigest()
                print(
                    "[settings][WARNING] SECRET_KEY demasiado corto (",
                    len(val),
                    "caracteres)",
                    "→ derivando SHA-256 para entorno",
                    env,
                )
                return SecretStr(derived)
            raise ValueError(f"SECRET_KEY debe tener al menos 32 caracteres (actual: {len(val)})")
        return v

    # Frontend
    FRONTEND_URL: str
    FRONTEND_MODULES_PATH: str | None = None

    # Cookies / CSRF
    SESSION_COOKIE_NAME: str = "bff_session"
    COOKIE_DOMAIN: str | None = None
    CSRF_COOKIE_NAME: str = "csrf_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # CORS
    CORS_ORIGINS: str | list[str] = Field(
        default=[],  # Empty by default - MUST be configured in production via env var
        description="Allowed origins for CORS (REQUIRED in production). Examples: 'https://www.gestiqcloud.com,https://admin.gestiqcloud.com' or list format. In development, defaults to empty (allow-all if not set).",
    )
    CORS_ALLOW_ORIGIN_REGEX: str | None = None
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: list[str] = [
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-CSRFToken",
        "X-CSRF",
        "X-Client-Version",
        "X-Client-Revision",
    ]
    # Permite string con comas o lista JSON
    ALLOWED_HOSTS: str | list[str] = Field(default_factory=list)

    # Base de datos
    DATABASE_URL: SecretStr
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 10  # segundos
    DB_STATEMENT_TIMEOUT_MS: int = 15000  # 15s

    # Redis (opcional)
    REDIS_URL: str | None = None

    # CSP / otros headers
    CSP_REPORT_URI: str | None = None
    CSP_DEV_HOSTS: str = Field(
        default="http://localhost:5173 http://localhost:5174",
        description="Hosts permitidos para Vite/HMR en desarrollo (space-separated)"
    )
    ALLOW_EMBED: bool = False
    HSTS_ENABLED: bool = True
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=(), payment=()"
    COOP_ENABLED: bool = False
    COEP_ENABLED: bool = False
    CORP_POLICY: str = "same-site"

    TENANT_NAMESPACE_UUID: str = Field(
        ..., description="Namespace para generar tenant UUIDs determinísticos"
    )
    ADMIN_SYSTEM_TENANT_ID: str = Field(
        "00000000-0000-0000-0000-000000000000", description="Tenant fijo para admins"
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
    DEFAULT_FROM_EMAIL: str = Field(
        default="",  # Empty - must be configured in environment
        description="Email address to use as sender (REQUIRED in production, e.g., 'noreply@gestiqcloud.com' or 'GestiqCloud <noreply@gestiqcloud.com>')"
    )
    EMAIL_DEV_LOG_ONLY: bool = False

    # Password reset/link base
    PASSWORD_RESET_URL_BASE: str | None = None
    print(PASSWORD_RESET_URL_BASE)
    # Uploads / Static user files
    UPLOADS_DIR: str = "uploads"
    UPLOADS_MOUNT_ENABLED: bool = True
    MAX_REQUEST_BYTES: int = 5 * 1024 * 1024
    GZIP_ENABLED: bool = True

    # Fase D - IA Configurable
    IMPORT_AI_PROVIDER: Literal["local", "openai", "azure"] = Field(
        default="local",
        description="AI provider for document classification (local | openai | azure)",
    )
    IMPORT_AI_CONFIDENCE_THRESHOLD: float = Field(
        default=0.7,
        description="Confidence threshold to trigger AI enhancement (use AI if < threshold)",
    )
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = Field(
        default="gpt-3.5-turbo", description="OpenAI model to use for classification"
    )
    AZURE_OPENAI_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    IMPORT_AI_CACHE_ENABLED: bool = Field(
        default=True, description="Enable caching of AI classifications"
    )
    IMPORT_AI_CACHE_TTL: int = Field(default=86400, description="Cache TTL in seconds")  # 24 hours
    IMPORT_AI_LOG_TELEMETRY: bool = Field(
        default=True, description="Log AI classification telemetry for accuracy tracking"
    )
    IMPORT_CONFIRMATION_THRESHOLD: float = Field(
        default=0.7,
        description="Confidence threshold below which user confirmation is required before processing",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v: str | list[str]) -> list[str]:
        """
        Parse CORS_ORIGINS from string (comma-separated) or list.
        
        In production, validates that:
        - Origins are configured
        - No localhost/127.0.0.1 allowed
        """
        if isinstance(v, str):
            origins = [o.strip() for o in v.split(",") if o.strip()]
        else:
            origins = v if isinstance(v, list) else []
        
        # Production validation
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production":
            if not origins:
                raise ValueError(
                    "CORS_ORIGINS is empty in production. "
                    "Set CORS_ORIGINS env var (e.g., https://www.gestiqcloud.com,https://admin.gestiqcloud.com)"
                )
            
            # Validate no localhost
            dangerous_origins = [o for o in origins if "localhost" in o.lower() or "127.0.0.1" in o]
            if dangerous_origins:
                raise ValueError(
                    f"CORS_ORIGINS contains localhost in production: {dangerous_origins}. "
                    "Use real domains only."
                )
        
        return origins

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

    @field_validator(
        "EMAIL_HOST",
        "EMAIL_HOST_USER",
        "EMAIL_HOST_PASSWORD",
        "DEFAULT_FROM_EMAIL",
        mode="before",
    )
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
        allowed = (
            "HS256",
            "HS384",
            "HS512",
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
        )
        if alg not in allowed:
            raise ValueError(f"JWT_ALGORITHM inválido: {alg}")
        return alg

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL.get_secret_value()
        return (
            url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url
        )

    @property
    def is_prod(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"
    
    @property
    def ENV(self) -> str:
        """Alias for ENVIRONMENT for backward compatibility."""
        return self.ENVIRONMENT

    @ENV.setter
    def ENV(self, value: str) -> None:
        self.ENVIRONMENT = value

    def assert_required_for_production(self):
        """Verifica que todas las variables críticas estén definidas en producción."""
        if self.ENVIRONMENT != "production":
            return  # No verificar en desarrollo

        required_vars = [
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "FRONTEND_URL",
            "DATABASE_URL",
            "SESSION_COOKIE_NAME",
            "CSRF_COOKIE_NAME",
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
