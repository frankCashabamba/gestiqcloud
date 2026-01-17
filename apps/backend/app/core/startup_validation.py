"""
Validación de configuración crítica al arranque de la aplicación.

Asegura que variables de entorno obligatorias estén configuradas
antes de que la app intente usar features que dependen de ellas.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("app.startup_validation")


class ConfigValidationError(Exception):
    """Excepción cuando falta configuración crítica."""
    pass


def validate_critical_config() -> None:
    """
    Valida que todas las variables críticas estén configuradas.
    
    Lanza ConfigValidationError si algo está mal.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
    validation_errors: list[str] = []
    
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
        if not redis_url or "localhost" in redis_url or "127.0.0.1" in redis_url:
            validation_errors.append(
                "❌ REDIS_URL not configured or points to localhost. "
                "Production must use external Redis. "
                "Example: REDIS_URL=redis://cache.internal:6379/1"
            )
        
        # 3. Database configuration
        db_url = os.getenv("DATABASE_URL", "").strip()
        if not db_url or "localhost" in db_url or "127.0.0.1" in db_url:
            validation_errors.append(
                "❌ DATABASE_URL not configured or points to localhost. "
                "Example: DATABASE_URL=postgresql://user:pass@db.internal/gestiqcloud"
            )
        
        # 4. CORS configuration
        cors_origins = os.getenv("CORS_ORIGINS", "").strip()
        if not cors_origins:
            validation_errors.append(
                "❌ CORS_ORIGINS not configured. Required in production.\n"
                "   Example: CORS_ORIGINS=https://www.gestiqcloud.com,https://admin.gestiqcloud.com"
            )
        else:
            # Validate no localhost in production
            origins_lower = cors_origins.lower()
            if "localhost" in origins_lower or "127.0.0.1" in origins_lower:
                validation_errors.append(
                    f"❌ CORS_ORIGINS contains localhost. Not allowed in production.\n"
                    f"   Value: {cors_origins}"
                )
    
    else:
        # Development: validaciones menos estrictas pero aún recomendaciones
        logger.info("🔓 Validating DEVELOPMENT configuration...")
        
        # Avisos (no fatales)
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
    
    # Si hay errores críticos, levantamos excepción
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
        # Check environment variables for certificate passwords
        # Format: CERT_PASSWORD_{TENANT_ID}_{COUNTRY}
        # Example: CERT_PASSWORD_tenant-123_ECU=password123
        #          CERT_PASSWORD_tenant-123_ESP=password456
        # For production, validate at least one is configured
        from app.config.settings import settings
        
        if settings.is_prod:
            # In production, require specific configuration
            logger.warning(
                "E-invoicing in production requires CERT_PASSWORD_{TENANT_ID}_{COUNTRY} "
                "configured in environment or AWS Secrets Manager. "
                "Example: CERT_PASSWORD_tenant-id_ECU=password123"
            )
        return True
    
    return True


def get_critical_config(key: str) -> Optional[str]:
    """
    Obtiene una variable crítica y valida que no es un fallback peligroso.
    
    Args:
        key: Nombre de la variable
        
    Returns:
        Valor de la variable o None si no está configurada
        
    Raises:
        ConfigValidationError: Si la variable tiene un valor peligroso (localhost)
    """
    value = os.getenv(key, "").strip()
    
    if not value:
        return None
    
    # Validar que no es localhost
    if key in ["REDIS_URL", "DATABASE_URL", "VITE_ELECTRIC_URL"]:
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment == "production" and ("localhost" in value or "127.0.0.1" in value):
            raise ConfigValidationError(
                f"{key} contains localhost in production: {value}"
            )
    
    return value
