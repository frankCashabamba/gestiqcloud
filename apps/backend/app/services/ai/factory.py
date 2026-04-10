"""
AI Provider Factory - Crea y gestiona proveedores segun configuracion.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from app.services.ai.base import AIModel, AITask, BaseAIProvider
from app.services.ai.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)

_OLLAMA_SAFE_DEFAULT_MODEL = AIModel.LLAMA3_1_8B.value
_OLLAMA_BLOCKED_MODEL_PREFIXES = ("qwen2.5-coder", "qwen2.5")
_OLLAMA_DEFAULT_TIMEOUT_SECONDS = 30.0


def _sanitize_ollama_model(raw_model: Any) -> tuple[str, str, str | None]:
    requested = str(raw_model or "").strip()
    if not requested:
        return _OLLAMA_SAFE_DEFAULT_MODEL, "default", None

    lowered = requested.lower()
    if lowered.startswith(_OLLAMA_BLOCKED_MODEL_PREFIXES):
        return _OLLAMA_SAFE_DEFAULT_MODEL, "legacy_blocked", requested

    return requested, "env", requested


def _sanitize_ollama_timeout(raw_timeout: Any) -> tuple[float, str, str | None]:
    requested_text = str(raw_timeout or "").strip()
    if not requested_text:
        return _OLLAMA_DEFAULT_TIMEOUT_SECONDS, "default", None

    try:
        requested = float(requested_text)
    except (TypeError, ValueError):
        return _OLLAMA_DEFAULT_TIMEOUT_SECONDS, "default_invalid", requested_text

    if requested <= 0:
        return _OLLAMA_DEFAULT_TIMEOUT_SECONDS, "default_invalid", requested_text

    if requested > _OLLAMA_DEFAULT_TIMEOUT_SECONDS:
        return _OLLAMA_DEFAULT_TIMEOUT_SECONDS, "env_capped", requested_text

    return requested, "env", requested_text


class AIProviderFactory:
    """Factory que gestiona instancias de proveedores IA."""

    _instances: dict[str, BaseAIProvider] = {}
    _primary_provider: str = "ollama"
    _fallback_chain: list[str] = ["ollama"]
    _supported_providers: tuple[str, ...] = ("ollama",)

    @classmethod
    def initialize(cls) -> None:
        """Inicializa solo el proveedor Ollama."""
        cls._primary_provider = "ollama"
        cls._fallback_chain = ["ollama"]
        logger.info("AI provider locked to Ollama")

        cls._create_provider("ollama")

    @classmethod
    def _create_provider(cls, name: str) -> None:
        """Crea instancia de proveedor especifico."""
        if name != "ollama":
            logger.warning("Unknown or disabled provider: %s", name)
            return

        config = cls._get_provider_config(name)
        try:
            cls._instances[name] = OllamaProvider(config)
        except Exception as exc:
            logger.error("Error creating provider %s: %s", name, exc)

    @classmethod
    def _get_provider_config(cls, name: str) -> dict[str, Any]:
        """Obtiene configuracion del proveedor desde env vars."""
        if name == "ollama":
            model, model_source, model_requested = _sanitize_ollama_model(os.getenv("OLLAMA_MODEL"))
            timeout, timeout_source, timeout_requested = _sanitize_ollama_timeout(
                os.getenv("OLLAMA_TIMEOUT")
            )
            if model_source == "legacy_blocked":
                logger.warning(
                    "OLLAMA_MODEL legacy value ignored requested=%s resolved=%s",
                    model_requested,
                    model,
                )
            if timeout_source == "env_capped":
                logger.warning(
                    "OLLAMA_TIMEOUT capped requested=%s effective=%.1fs",
                    timeout_requested,
                    timeout,
                )
            return {
                "url": (
                    os.getenv("OLLAMA_BASE_URL")
                    or os.getenv("OLLAMA_URL")
                    or "http://127.0.0.1:11434"
                ),
                "endpoint": os.getenv("OLLAMA_ENDPOINT", "/api/chat"),
                "model": model,
                "model_requested": model_requested,
                "model_source": model_source,
                "timeout": timeout,
                "timeout_requested": timeout_requested,
                "timeout_source": timeout_source,
                "health_check_timeout": float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "5")),
                "max_concurrency": os.getenv("OLLAMA_MAX_CONCURRENCY", "4"),
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
