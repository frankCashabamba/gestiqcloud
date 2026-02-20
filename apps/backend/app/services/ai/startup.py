"""
Startup initialization for AI provider factory.
"""

from __future__ import annotations

import logging

from app.services.ai import AIProviderFactory

logger = logging.getLogger(__name__)


async def initialize_ai_providers() -> None:
    """
    Initialize all AI providers on startup.
    """
    try:
        logger.info("Initializing AI providers...")
        AIProviderFactory.initialize()

        health = await AIProviderFactory.health_check_all()
        for provider_name, is_healthy in health.items():
            status = "available" if is_healthy else "unavailable"
            logger.info("AI provider %s: %s", provider_name, status)

        available = sum(1 for value in health.values() if value)
        if available == 0:
            logger.warning(
                "No AI provider is available. Check AI_PROVIDER, OLLAMA_BASE_URL/OLLAMA_URL, "
                "OVHCLOUD_BASE_URL/OVHCLOUD_API_URL, and OPENAI_API_KEY."
            )
        else:
            logger.info("%s/%s AI providers available", available, len(health))

        logger.info("AI primary provider: %s", AIProviderFactory._primary_provider)
        logger.info("AI fallback chain: %s", " -> ".join(AIProviderFactory._fallback_chain))
    except Exception as exc:
        logger.error("Error initializing AI providers: %s", exc, exc_info=True)


async def shutdown_ai_providers() -> None:
    """
    Cleanup on shutdown.
    """
    logger.info("Shutting down AI providers...")
