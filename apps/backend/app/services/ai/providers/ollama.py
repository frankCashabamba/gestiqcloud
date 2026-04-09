"""
Ollama AI Provider - Local LLM via Ollama
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider, model_name

logger = logging.getLogger(__name__)


# Keep concurrency bounded per provider instance. Sharing a module-level
# semaphore creates avoidable cross-tenant contention and hides real capacity.
def _ollama_max_concurrency(default: int = 1) -> int:
    raw = (os.getenv("OLLAMA_MAX_CONCURRENCY") or "").strip()
    try:
        return max(1, int(raw)) if raw else default
    except ValueError:
        return default


_logged_concurrency_configs: set[tuple[str, int]] = set()
_tags_cache: dict[str, tuple[float, list[str]]] = {}
_health_cache: dict[str, tuple[float, bool]] = {}
_CONTROLLED_EXTRACTION_MODELS = {
    AIModel.LLAMA3_1_8B.value,
    AIModel.MISTRAL_7B.value,
}
_BLOCKED_MODEL_PREFIXES = ("qwen2.5-coder", "qwen2.5")


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(str(value).strip()))
    except (TypeError, ValueError, AttributeError):
        return default


def _model_parameter_size_b(model: str) -> float | None:
    """Best-effort parse of Ollama model size from the tag name."""
    normalized = model_name(model).lower()
    match = re.search(r":(\d+(?:\.\d+)?)([bm])(?:$|[^a-z0-9])", normalized)
    if not match:
        return None
    size = float(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return size / 1000.0
    return size


def _is_non_extraction_model(model: str) -> bool:
    normalized = model_name(model).lower()
    return ":cloud" in normalized or "embed" in normalized


def _is_blocked_legacy_model(model: str | None) -> bool:
    normalized = model_name(model).lower()
    return bool(normalized) and normalized.startswith(_BLOCKED_MODEL_PREFIXES)


def _first_allowed_model(available_models: list[str]) -> str | None:
    for model in available_models:
        normalized = model_name(model)
        if not normalized:
            continue
        if _is_non_extraction_model(normalized) or _is_blocked_legacy_model(normalized):
            continue
        return normalized
    return None


def _cache_ttl(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


class OllamaProvider(BaseAIProvider):
    """
    Proveedor local Ollama para desarrollo/testing.
    Requiere Ollama corriendo localmente en puerto 11434.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("ollama", config)
        self.base_url = (config.get("url") or "http://127.0.0.1:11434").rstrip("/")
        self.endpoint = (config.get("endpoint") or "/api/chat").strip()
        # Allow passing full endpoint URL (e.g., http://127.0.0.1:11434/api/chat)
        if self.endpoint.startswith("http"):
            self._endpoint_url = self.endpoint.rstrip("/")
        else:
            normalized_endpoint = (
                self.endpoint if self.endpoint.startswith("/") else f"/{self.endpoint}"
            )
            self._endpoint_url = f"{self.base_url}{normalized_endpoint}"

        self.use_chat_api = "chat" in self.endpoint
        self.default_model = model_name(config.get("model")) or AIModel.LLAMA3_1_8B.value
        try:
            parsed_timeout = float(str(config.get("timeout", 30.0)).strip())
            self.request_timeout = parsed_timeout if parsed_timeout > 0 else 30.0
        except (TypeError, ValueError, AttributeError):
            self.request_timeout = 30.0
        self.max_concurrency = _coerce_positive_int(
            config.get("max_concurrency"),
            _ollama_max_concurrency(),
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        config_key = (
            self.base_url,
            self.max_concurrency,
            self.default_model,
            round(self.request_timeout, 3),
        )
        if config_key not in _logged_concurrency_configs:
            logger.info(
                "Ollama configured base_url=%s endpoint=%s max_concurrency=%s timeout=%.1fs timeout_source=%s model=%s model_source=%s",
                self.base_url,
                self.endpoint,
                self.max_concurrency,
                self.request_timeout,
                self.config.get("timeout_source") or "default",
                self.default_model,
                self.config.get("model_source") or "default",
            )
            _logged_concurrency_configs.add(config_key)

    async def _get_available_models(self, timeout: float = 3.0) -> list[str]:
        """Cache /api/tags to avoid repeated round-trips on every request."""
        ttl = _cache_ttl("OLLAMA_TAGS_CACHE_TTL", 30.0)
        now = time.monotonic()
        cached = _tags_cache.get(self.base_url)
        if cached and now - cached[0] <= ttl:
            return list(cached[1])

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = [
                str(model.get("name") or "").strip() for model in resp.json().get("models", [])
            ]
        models = [model for model in models if model]
        _tags_cache[self.base_url] = (now, models)
        _health_cache[self.base_url] = (now, True)
        return list(models)

    async def _available_model_set(self, timeout: float | None = None) -> set[str]:
        models = await self._get_available_models(timeout=timeout or self._health_check_timeout)
        return {model_name(model) for model in models if model_name(model)}

    async def validate_model(self, model: AIModel | str) -> bool:
        normalized = model_name(model)
        if not normalized or _is_blocked_legacy_model(normalized):
            return False
        try:
            available = await self._available_model_set(timeout=self._health_check_timeout)
        except Exception:
            available = set()
        return normalized in available

    async def _resolve_model_for_request(self, request: AIRequest) -> tuple[str, str | None, str]:
        """Resolve a usable model before the POST request goes out."""
        configured = model_name(self.default_model) or AIModel.LLAMA3_1_8B.value
        explicit = model_name(request.model)
        try:
            available_models = await self._get_available_models(timeout=self._health_check_timeout)
        except Exception as exc:
            logger.warning("No se pudo consultar /api/tags en Ollama: %s", exc)
            available_models = []

        available_set = {model_name(item) for item in available_models if model_name(item)}
        if explicit:
            if _is_blocked_legacy_model(explicit):
                logger.warning(
                    "Ignoring blocked legacy Ollama model task=%s requested=%s",
                    request.task.value,
                    explicit,
                )
            elif explicit in available_set:
                return explicit, None, "explicit_request"
            else:
                return (
                    explicit,
                    f"Modelo Ollama no disponible: {explicit}",
                    "explicit_request_missing",
                )

        if configured and configured in available_set and not _is_blocked_legacy_model(configured):
            return configured, None, "configured_default"

        if request.task == AITask.EXTRACTION:
            extraction_model = self._best_extraction_model(available_models)
            if extraction_model:
                reason = (
                    "controlled_extraction_configured"
                    if extraction_model == configured
                    else "controlled_extraction_preferred"
                )
                return extraction_model, None, reason

            return (
                AIModel.LLAMA3_1_8B.value,
                "No hay modelos de extraccion controlados disponibles",
                "controlled_extraction_missing",
            )

        if available_models:
            fallback_model = _first_allowed_model(available_models)
            if fallback_model:
                return fallback_model, None, "first_available"

        if configured and not _is_blocked_legacy_model(configured):
            return configured, None, "configured_default_fallback"

        return (
            AIModel.LLAMA3_1_8B.value,
            f"No hay modelos Ollama disponibles en {self.base_url}",
            "no_available_models",
        )

    async def call(self, request: AIRequest) -> AIResponse:
        """Llama a Ollama API."""
        start_time = time.perf_counter()
        requested_model = model_name(request.model)
        selected_model, model_error, selection_reason = await self._resolve_model_for_request(
            request
        )
        if model_error:
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=model_error,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                metadata={
                    "provider": "ollama",
                    "model_requested": requested_model or None,
                    "model_resolved": selected_model,
                    "selection_reason": selection_reason,
                    "timeout_seconds": self.request_timeout,
                    "timeout_source": self.config.get("timeout_source") or "default",
                },
            )

        logger.info(
            "Ollama request task=%s requested_model=%s resolved_model=%s reason=%s timeout=%.1fs timeout_source=%s",
            request.task.value,
            requested_model or "default",
            selected_model,
            selection_reason,
            self.request_timeout,
            self.config.get("timeout_source") or "default",
        )

        try:
            prompt = self._prepare_prompt(request)
            if self.use_chat_api:
                options: dict[str, Any] = {"temperature": request.temperature}
                if request.max_tokens:
                    options["num_predict"] = request.max_tokens
                messages = request.messages or [{"role": "user", "content": prompt}]

                payload = {
                    "model": selected_model,
                    "messages": messages,
                    "stream": False,
                    "options": options,
                }
            else:
                payload = {
                    "model": selected_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": request.temperature,
                }
                if request.max_tokens:
                    payload["num_predict"] = request.max_tokens

            async with self._semaphore:
                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    response = await client.post(self._endpoint_url, json=payload)
                    response.raise_for_status()
                    data = response.json()

            if self.use_chat_api:
                content = (
                    (data.get("message") or {}).get("content") or data.get("response") or ""
                ).strip()
                tokens_used = data.get("eval_count") or data.get("total_tokens")
                eval_duration = data.get("eval_duration") or data.get("total_duration")
            else:
                content = data.get("response", "").strip()
                tokens_used = data.get("eval_count", 0)
                eval_duration = data.get("eval_duration")

            if not content:
                return AIResponse(
                    task=request.task,
                    content="",
                    model=selected_model,
                    error="Respuesta vacía de Ollama",
                    processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return AIResponse(
                task=request.task,
                content=content,
                model=selected_model,
                tokens_used=tokens_used or 0,
                processing_time_ms=elapsed_ms,
                metadata={
                    "provider": "ollama",
                    "temperature": request.temperature,
                    "endpoint": self.endpoint,
                    "max_concurrency": self.max_concurrency,
                    "model_requested": requested_model or None,
                    "model_resolved": selected_model,
                    "selection_reason": selection_reason,
                    "timeout_seconds": self.request_timeout,
                    "timeout_source": self.config.get("timeout_source") or "default",
                    "eval_duration_ns": eval_duration,
                },
            )

        except httpx.ConnectError as e:
            logger.error("Error conectando a Ollama: %s", e)
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"No se puede conectar a Ollama: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
        except httpx.ReadTimeout:
            logger.error(
                "Ollama timeout tras %.0fs para modelo '%s' en %s",
                self.request_timeout,
                selected_model,
                self._endpoint_url,
            )
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"Ollama timeout ({self.request_timeout:.0f}s)",
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            details = ""
            if e.response is not None:
                try:
                    details = (e.response.text or "").strip()
                except Exception:
                    details = ""
            logger.warning(
                "Ollama returned HTTP %s for model '%s' at %s. details=%s",
                status,
                selected_model,
                self._endpoint_url,
                details[:300],
            )
            error_msg = f"Ollama HTTP {status}"
            if details:
                error_msg = f"{error_msg}: {details[:300]}"
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=error_msg,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            logger.error("Error en Ollama call: %s", e, exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"Error Ollama: {str(e)}",
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

    async def health_check(self) -> bool:
        """Verifica que Ollama este disponible."""
        ttl = _cache_ttl("OLLAMA_HEALTH_CACHE_TTL", 15.0)
        now = time.monotonic()
        cached = _health_cache.get(self.base_url)
        if cached and now - cached[0] <= ttl:
            return cached[1]

        try:
            await self._get_available_models(timeout=self._health_check_timeout)
            _health_cache[self.base_url] = (now, True)
            return True
        except Exception:
            _health_cache[self.base_url] = (now, False)
            return False

    def _best_extraction_model(self, available_models: list[str] | None = None) -> str | None:
        """Find a controlled locally available model for document extraction.

        The extraction path is whitelist-only to avoid hidden qwen fallbacks.
        """
        try:
            available = available_models or self._get_available_models(timeout=3.0)
            available_set = {model_name(model) for model in available if model_name(model)}
            ordered_candidates = [
                model_name(self.default_model),
                AIModel.LLAMA3_1_8B.value,
                AIModel.MISTRAL_7B.value,
            ]
            seen: set[str] = set()
            for candidate in ordered_candidates:
                normalized = model_name(candidate)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                if normalized not in _CONTROLLED_EXTRACTION_MODELS:
                    continue
                if normalized in available_set:
                    logger.info("Using controlled extraction model: %s", normalized)
                    return normalized
            return None
        except Exception:
            return None

    def get_default_model(self, task: AITask) -> str:
        """Modelo por defecto para Ollama.

        El modelo configurado se valida en tiempo de ejecución antes de llamar.
        Si no hay configuracion valida, usamos Llama 3.1 8B como fallback seguro.
        """
        configured = model_name(self.default_model)
        if configured and not _is_blocked_legacy_model(configured):
            return configured
        return AIModel.LLAMA3_1_8B.value

    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados historicamente por esta app para Ollama."""
        return [
            AIModel.LLAMA3_1_8B,
            AIModel.MISTRAL_7B,
            AIModel.LLAMA3_1_70B,
            AIModel.NEURAL_CHAT,
        ]
