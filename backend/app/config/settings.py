from typing import List, Optional, Union, Literal
from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # General
    app_name: str = "GestiqCloud"
    debug: bool = False
    ENV: Literal["development", "production"] = "development"

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

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:5174"],
        description="Orígenes permitidos (lista o string con comas)."
    )
    CORS_ALLOW_ORIGIN_REGEX: Optional[str] = None
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET","POST","PUT","PATCH","DELETE","OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Authorization","Content-Type","X-CSRF-Token","X-CSRF"]

    # Base de datos
    DATABASE_URL: SecretStr

    # CSP / otros headers
    CSP_REPORT_URI: Optional[str] = None
    ALLOW_EMBED: bool = False
    HSTS_ENABLED: bool = True
    REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=(), payment=()"
    COOP_ENABLED: bool = False
    COEP_ENABLED: bool = False
    CORP_POLICY: str = "same-site"
       # ...
    TENANT_NAMESPACE_UUID: str = Field(..., description="Namespace para generar tenant UUIDs determinísticos")  
    ADMIN_SYSTEM_TENANT_ID: str = Field("00000000-0000-0000-0000-000000000000",
                                        description="Tenant fijo para admins")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("FRONTEND_URL")
    @classmethod
    def ensure_frontend_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("FRONTEND_URL debe incluir http(s)://")
        return v

    @property
    def database_url(self) -> str:
        url = self.DATABASE_URL.get_secret_value()
        print("DB URL type:",url)
        return url.replace("postgres://", "postgresql://", 1) if url.startswith("postgres://") else url

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

        missing = []
        for var in required_vars:
            value = getattr(self, var, None)
            if isinstance(value, SecretStr):
                if not value.get_secret_value():
                    missing.append(var)
            elif not value:
                missing.append(var)

        if missing:
            raise RuntimeError(
                f"❌ Variables de entorno obligatorias faltantes para producción: {', '.join(missing)}"
            )


# Instancia global de configuración
settings = Settings()
settings.assert_required_for_production()
