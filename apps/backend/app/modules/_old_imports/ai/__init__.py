"""AI provider factory for imports module."""

from app.config.settings import settings

from .base import AIProvider
from .local_provider import LocalAIProvider
from .unified_provider import UnifiedServiceAIProvider

try:
    from .azure_provider import AzureOpenAIProvider as _AzureOpenAIProvider

    AzureOpenAIProvider: type | None = _AzureOpenAIProvider
except ImportError:
    AzureOpenAIProvider = None


async def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    """Return imports AI provider based on configuration."""
    provider_type = (provider_name or settings.IMPORT_AI_PROVIDER).lower()

    if provider_type == "local":
        return LocalAIProvider()

    if provider_type in ("ollama", "openai", "ovhcloud"):
        # Use the unified provider stack from app.services.ai.
        return UnifiedServiceAIProvider(provider_name=provider_type)

    if provider_type == "azure":
        if not AzureOpenAIProvider:
            raise RuntimeError(
                "Azure provider requires 'openai' package. Install with: pip install openai"
            )
        if not settings.AZURE_OPENAI_KEY:
            raise ValueError("AZURE_OPENAI_KEY not configured")
        if not settings.AZURE_OPENAI_ENDPOINT:
            raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
        return AzureOpenAIProvider(
            api_key=settings.AZURE_OPENAI_KEY,
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
        )

    raise ValueError(f"Unknown AI provider: {provider_type}")


_ai_provider_instances: dict[str, AIProvider] = {}


async def get_ai_provider_singleton(provider_name: str | None = None) -> AIProvider:
    """Get singleton imports AI provider instance."""
    key = (provider_name or settings.IMPORT_AI_PROVIDER).lower()
    provider = _ai_provider_instances.get(key)
    if provider is None:
        provider = await get_ai_provider(key)
        _ai_provider_instances[key] = provider
    return provider


def reset_ai_provider():
    """Reset singleton provider (useful in tests)."""
    _ai_provider_instances.clear()


__all__ = [
    "AIProvider",
    "LocalAIProvider",
    "UnifiedServiceAIProvider",
    "get_ai_provider",
    "get_ai_provider_singleton",
    "reset_ai_provider",
]
