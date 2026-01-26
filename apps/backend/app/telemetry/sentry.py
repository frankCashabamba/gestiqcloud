"""Sentry error tracking integration."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_sentry() -> bool:
    """Initialize Sentry SDK if SENTRY_DSN is configured.

    Env vars:
      - SENTRY_DSN: The Sentry DSN (required to enable)
      - SENTRY_ENVIRONMENT: Environment name (default: development)
      - SENTRY_TRACES_SAMPLE_RATE: Trace sample rate 0.0-1.0 (default: 0.1)
      - SENTRY_PROFILES_SAMPLE_RATE: Profile sample rate 0.0-1.0 (default: 0.1)

    Returns:
        True if Sentry was initialized, False otherwise.
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.debug("Sentry disabled: SENTRY_DSN not set")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        environment = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENV", "development"))
        traces_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        profiles_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_rate,
            profiles_sample_rate=profiles_rate,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
            ],
            send_default_pii=False,
        )

        logger.info("Sentry initialized for environment: %s", environment)
        return True

    except ImportError:
        logger.warning("Sentry SDK not installed, skipping initialization")
        return False
    except Exception as e:
        logger.warning("Failed to initialize Sentry: %s", e)
        return False


def capture_exception(error: Exception, **extra) -> None:
    """Capture an exception to Sentry if configured."""
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        pass
    except Exception:
        pass


def set_user(user_id: str, email: str | None = None, tenant_id: str | None = None) -> None:
    """Set user context for Sentry."""
    try:
        import sentry_sdk

        sentry_sdk.set_user(
            {
                "id": user_id,
                "email": email,
                "tenant_id": tenant_id,
            }
        )
    except ImportError:
        pass
    except Exception:
        pass
