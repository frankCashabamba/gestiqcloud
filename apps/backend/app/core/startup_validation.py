"""
Validación de configuración crítica al arranque de la aplicación.

Asegura que variables de entorno obligatorias estén configuradas
antes de que la app intente usar features que dependen de ellas.
"""

import logging
import os

logger = logging.getLogger("app.startup_validation")


class ConfigValidationError(Exception):
    """Excepción cuando falta configuración crítica."""

    pass


def _is_local_url(value: str) -> bool:
    value = (value or "").lower()
    return "localhost" in value or "127.0.0.1" in value


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def validate_critical_config() -> None:
    """
    Valida que todas las variables críticas estén configuradas.

    Lanza ConfigValidationError si algo está mal.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    validation_errors: list[str] = []

    allow_local_redis = _env_flag("ALLOW_LOCAL_REDIS_IN_PROD", default=False)
    allow_local_db = _env_flag("ALLOW_LOCAL_DB_IN_PROD", default=False)

    # En producción, validaciones más estrictas
    if environment == "production":
        logger.info("🔒 Validating PRODUCTION configuration...")

        # 1. Email configuration
        if not os.getenv("DEFAULT_FROM_EMAIL"):
            validation_errors.append(
                "❌ DEFAULT_FROM_EMAIL not configured. "
                "Required in production. "
                "Example: DEFAULT_FROM_EMAIL=no-reply@gestiqcloud.com"
            )

        # 2. Redis configuration
        redis_url = os.getenv("REDIS_URL", "").strip()
        if not redis_url:
            validation_errors.append(
                "❌ REDIS_URL not configured. " "Example: REDIS_URL=redis://cache.internal:6379/1"
            )
        elif _is_local_url(redis_url) and not allow_local_redis:
            validation_errors.append(
                "❌ REDIS_URL points to localhost in production. "
                "If this is a single-host self-hosted deployment, set "
                "ALLOW_LOCAL_REDIS_IN_PROD=true. "
                "Example: REDIS_URL=redis://127.0.0.1:6379/1"
            )

        # 3. Database configuration
        db_url = os.getenv("DATABASE_URL", "").strip()
        if not db_url:
            validation_errors.append(
                "❌ DATABASE_URL not configured. "
                "Example: DATABASE_URL=postgresql://user:pass@db.internal/gestiqcloud"
            )
        elif _is_local_url(db_url) and not allow_local_db:
            validation_errors.append(
                "❌ DATABASE_URL points to localhost in production. "
                "If this is a single-host self-hosted deployment, set "
                "ALLOW_LOCAL_DB_IN_PROD=true. "
                "Example: DATABASE_URL=postgresql://user:pass@127.0.0.1:5432/gestiqcloud"
            )

        # 4. CORS configuration
        cors_origins = os.getenv("CORS_ORIGINS", "").strip()
        if not cors_origins:
            validation_errors.append(
                "❌ CORS_ORIGINS not configured. Required in production.\n"
                "   Example: CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com"
            )
        else:
            origins_lower = cors_origins.lower()
            if "localhost" in origins_lower or "127.0.0.1" in origins_lower:
                validation_errors.append(
                    f"❌ CORS_ORIGINS contains localhost. Not allowed in production.\n"
                    f"   Value: {cors_origins}"
                )

        # 5. Secret keys - must not be placeholder values
        _PLACEHOLDER_SECRETS = {
            "your-secret-key-min-32-chars-change-in-production",
            "change-me",
            "secret",
            "changeme",
        }

        secret_key = os.getenv("SECRET_KEY", "").strip()
        if not secret_key or secret_key.lower() in _PLACEHOLDER_SECRETS:
            validation_errors.append(
                "❌ SECRET_KEY not configured or uses a placeholder value. "
                'Generate a strong secret: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

        jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
        if not jwt_secret or jwt_secret.lower() in _PLACEHOLDER_SECRETS:
            validation_errors.append(
                "❌ JWT_SECRET_KEY not configured or uses a placeholder value. "
                'Generate a strong secret: python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )

    else:
        # Development: validaciones menos estrictas pero aún recomendaciones
        logger.info("🔓 Validating DEVELOPMENT configuration...")

        if not os.getenv("DEFAULT_FROM_EMAIL"):
            logger.warning(
                "⚠️  DEFAULT_FROM_EMAIL not configured. "
                "Email features may not work. "
                "Set it: DEFAULT_FROM_EMAIL=dev@example.com"
            )

        if not os.getenv("REDIS_URL"):
            logger.warning(
                "⚠️  REDIS_URL not configured. "
                "Using fallback (may cause issues). "
                "Set it: REDIS_URL=redis://localhost:6379/0"
            )

    if validation_errors:
        error_message = "\n".join(validation_errors)
        logger.error(
            f"\n{'='*70}\n"
            f"CRITICAL CONFIGURATION ERROR\n"
            f"{'='*70}\n"
            f"{error_message}\n"
            f"{'='*70}"
        )
        raise ConfigValidationError(error_message)

    logger.info("✅ Configuration validation passed")


def validate_feature_config(feature: str) -> bool:
    """
    Valida si una feature específica está correctamente configurada.

    Returns:
        True si está bien configurada, False si no.
    """
    if feature == "email":
        from_email = os.getenv("DEFAULT_FROM_EMAIL", "").strip()
        if not from_email:
            logger.warning("Email feature disabled: DEFAULT_FROM_EMAIL not configured")
            return False
        return True

    elif feature == "electric":
        electric_url = os.getenv("VITE_ELECTRIC_URL", "").strip()
        if not electric_url:
            logger.warning("Electric feature disabled: VITE_ELECTRIC_URL not configured")
            return False
        return True

    elif feature == "einvoicing":
        from app.config.settings import settings

        if settings.is_prod:
            logger.warning(
                "E-invoicing in production requires CERT_PASSWORD_{TENANT_ID}_{COUNTRY} "
                "configured in environment or AWS Secrets Manager. "
                "Example: CERT_PASSWORD_tenant-id_ECU=password123"
            )
        return True

    return True


def get_critical_config(key: str) -> str | None:
    """
    Obtiene una variable crítica y valida que no es un fallback peligroso.

    Args:
        key: Nombre de la variable

    Returns:
        Valor de la variable o None si no está configurada

    Raises:
        ConfigValidationError: Si la variable tiene un valor peligroso
    """
    value = os.getenv(key, "").strip()

    if not value:
        return None

    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        allow_local_redis = _env_flag("ALLOW_LOCAL_REDIS_IN_PROD", default=False)
        allow_local_db = _env_flag("ALLOW_LOCAL_DB_IN_PROD", default=False)

        if key == "REDIS_URL" and _is_local_url(value) and not allow_local_redis:
            raise ConfigValidationError(f"{key} contains localhost in production: {value}")

        if key == "DATABASE_URL" and _is_local_url(value) and not allow_local_db:
            raise ConfigValidationError(f"{key} contains localhost in production: {value}")

        if key == "VITE_ELECTRIC_URL" and _is_local_url(value):
            raise ConfigValidationError(f"{key} contains localhost in production: {value}")

    return value
