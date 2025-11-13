"""AI provider factory and imports for Fase D IA Configurable."""

from typing import Optional

from app.config.settings import settings

from .base import AIProvider
from .local_provider import LocalAIProvider

# Lazy imports para evitar dependencias innecesarias
_openai_provider = None
_azure_provider = None

try:
    from .openai_provider import OpenAIProvider
except ImportError:
    OpenAIProvider = None

try:
    from .azure_provider import AzureOpenAIProvider
except ImportError:
    AzureOpenAIProvider = None


async def get_ai_provider() -> AIProvider:
    """Factory para obtener proveedor IA según configuración."""
    provider_type = settings.IMPORT_AI_PROVIDER.lower()

    if provider_type == "local":
        return LocalAIProvider()

    elif provider_type == "openai":
        if not OpenAIProvider:
            raise RuntimeError(
                "OpenAI provider requires 'openai' package. " "Install with: pip install openai"
            )
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )

    elif provider_type == "azure":
        if not AzureOpenAIProvider:
            raise RuntimeError(
                "Azure provider requires 'openai' package. " "Install with: pip install openai"
            )
        if not settings.AZURE_OPENAI_KEY:
            raise ValueError("AZURE_OPENAI_KEY not configured")
        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
        return AzureOpenAIProvider(
            api_key=settings.AZURE_OPENAI_KEY,
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )

    else:
        raise ValueError(f"Unknown AI provider: {provider_type}")


# Singleton
_ai_provider_instance: AIProvider | None = None


async def get_ai_provider_singleton() -> AIProvider:
    """Get AI provider (cached singleton)."""
    global _ai_provider_instance
    if _ai_provider_instance is None:
        _ai_provider_instance = await get_ai_provider()
    return _ai_provider_instance


def reset_ai_provider():
    """Reset the singleton (útil para tests)."""
    global _ai_provider_instance
    _ai_provider_instance = None


__all__ = [
    "AIProvider",
    "LocalAIProvider",
    "get_ai_provider",
    "get_ai_provider_singleton",
    "reset_ai_provider",
]
