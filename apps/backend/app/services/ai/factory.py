"""
AI Provider Factory - Crea y gestiona proveedores segun configuracion.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.services.ai.base import AITask, BaseAIProvider
from app.services.ai.providers.ollama import OllamaProvider
from app.services.ai.providers.openai import OpenAIProvider
from app.services.ai.providers.ovhcloud import OVHCloudProvider

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory que gestiona instancias de proveedores IA."""

    _instances: dict[str, BaseAIProvider] = {}
    _primary_provider: str = "ollama"
    _fallback_chain: list[str] = ["ollama", "ovhcloud", "openai"]
    _supported_providers: tuple[str, ...] = ("ollama", "ovhcloud", "openai")

    @classmethod
    def initialize(cls) -> None:
        """Inicializa proveedores basado en configuracion de entorno."""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        requested_provider = os.getenv("AI_PROVIDER", "").strip().lower()

        if requested_provider in cls._supported_providers:
            cls._primary_provider = requested_provider
            cls._fallback_chain = [requested_provider] + [
                provider for provider in cls._supported_providers if provider != requested_provider
            ]
            logger.info(
                "AI_PROVIDER=%s: explicit provider priority enabled",
                requested_provider,
            )
        elif environment == "production":
            cls._primary_provider = "ovhcloud"
            cls._fallback_chain = ["ovhcloud", "openai"]
            logger.info("Production mode: OVHCloud primary, OpenAI fallback")
        else:
            cls._primary_provider = "ollama"
            cls._fallback_chain = ["ollama", "openai"]
            logger.info("Development mode: Ollama primary, OpenAI fallback")

        cls._create_provider("ollama")
        cls._create_provider("ovhcloud")
        cls._create_provider("openai")

    @classmethod
    def _create_provider(cls, name: str) -> None:
        """Crea instancia de proveedor especifico."""
        config = cls._get_provider_config(name)

        try:
            if name == "ollama":
                cls._instances[name] = OllamaProvider(config)
            elif name == "ovhcloud":
                cls._instances[name] = OVHCloudProvider(config)
            elif name == "openai":
                cls._instances[name] = OpenAIProvider(config)
            else:
                logger.warning("Unknown provider: %s", name)
        except Exception as exc:
            logger.error("Error creating provider %s: %s", name, exc)

    @classmethod
    def _get_provider_config(cls, name: str) -> dict[str, Any]:
        """Obtiene configuracion del proveedor desde env vars."""
        if name == "ollama":
            return {
                "url": (
                    os.getenv("OLLAMA_BASE_URL")
                    or os.getenv("OLLAMA_URL")
                    or "http://localhost:11434"
                ),
                "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                "timeout": float(os.getenv("OLLAMA_TIMEOUT", "30")),
                "health_check_timeout": float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "5")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }

        if name == "ovhcloud":
            return {
                "url": (
                    os.getenv("OVHCLOUD_BASE_URL")
                    or os.getenv("OVHCLOUD_API_URL")
                    or "https://manager.eu.ovhcloud.com/api/v2"
                ),
                "api_key": os.getenv("OVHCLOUD_API_KEY"),
                "api_secret": os.getenv("OVHCLOUD_API_SECRET"),
                "service_name": os.getenv("OVHCLOUD_SERVICE_NAME", "ai"),
                "model": os.getenv("OVHCLOUD_MODEL", "gpt-4o"),
                "timeout": float(os.getenv("OVHCLOUD_TIMEOUT", "60")),
                "health_check_timeout": float(os.getenv("OVHCLOUD_HEALTH_TIMEOUT", "10")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }

        if name == "openai":
            return {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "timeout": float(os.getenv("OPENAI_TIMEOUT", "30")),
                "health_check_timeout": float(os.getenv("OPENAI_HEALTH_TIMEOUT", "5")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }

        return {}

    @classmethod
    def get_provider(cls, name: str | None = None) -> BaseAIProvider | None:
        """Obtiene proveedor especifico o primario."""
        if not cls._instances:
            cls.initialize()

        target = name or cls._primary_provider
        return cls._instances.get(target)

    @classmethod
    async def get_available_provider(cls, task: AITask | None) -> BaseAIProvider | None:
        """
        Obtiene primer proveedor disponible en cadena de fallback.

        `task` is currently reserved for task-aware selection.
        """
        if not cls._instances:
            cls.initialize()

        for provider_name in cls._fallback_chain:
            provider = cls._instances.get(provider_name)
            if provider and await provider.health_check():
                logger.debug("Available provider: %s", provider_name)
                return provider

        logger.warning("No AI providers available")
        return None

    @classmethod
    def list_providers(cls) -> list[str]:
        """Lista proveedores disponibles."""
        if not cls._instances:
            cls.initialize()
        return list(cls._instances.keys())

    @classmethod
    def get_all_providers(cls) -> list[BaseAIProvider]:
        """Retorna todas las instancias creadas de proveedores IA."""
        if not cls._instances:
            cls.initialize()
        return [provider for provider in cls._instances.values() if provider is not None]

    @classmethod
    async def health_check_all(cls) -> dict[str, bool]:
        """Verifica salud de todos los proveedores."""
        if not cls._instances:
            cls.initialize()

        results: dict[str, bool] = {}
        for name, provider in cls._instances.items():
            try:
                results[name] = await provider.health_check()
            except Exception as exc:
                logger.error("Error in health_check for %s: %s", name, exc)
                results[name] = False

        return results
