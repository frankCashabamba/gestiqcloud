"""
Ollama AI Provider - Local LLM via Ollama

Refactor goals:
- Keep the provider focused on discovery/validation/HTTP calls
- Remove task-specific extraction policy from the provider
- Reuse a single AsyncClient per provider instance
- Make model resolution deterministic and simple
- Avoid async/sync mixing bugs in model discovery
- Improve logging and cache handling
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider, model_name

logger = logging.getLogger(__name__)

_logged_configs: set[tuple[str, str, int, float, str]] = set()
_tags_cache: dict[tuple[str, str], tuple[float, list[str]]] = {}
_health_cache: dict[tuple[str, str], tuple[float, bool]] = {}
_DEFAULT_ALLOWED_EXTRACTION_MODELS: tuple[str, ...] = (
    AIModel.QWEN3_8B.value,
)


@dataclass(frozen=True)
class ModelResolution:
    model: str
    reason: str
    error: str | None = None


class SelectionReason:
    EXPLICIT_REQUEST = "explicit_request"
    EXPLICIT_REQUEST_MISSING = "explicit_request_missing"
    CONFIGURED_DEFAULT = "configured_default"
    CONFIGURED_DEFAULT_FALLBACK = "configured_default_fallback"
    ALLOWED_EXTRACTION_MODEL = "allowed_extraction_model"
    FIRST_AVAILABLE = "first_available"
    NO_ALLOWED_EXTRACTION_MODEL = "no_allowed_extraction_model"
    NO_AVAILABLE_MODELS = "no_available_models"


class OllamaProvider(BaseAIProvider):
    """
    Transport/provider layer for Ollama.

    IMPORTANT:
    - This provider does transport + model selection safety.
    - For AITask.EXTRACTION it enforces a stricter model policy:
      * no first-available fallback
      * no non-extraction model families (vision/embed/adapter)
      * only explicitly requested/configured/allow-listed extraction models
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("ollama", config)

        self.base_url = self._normalize_base_url(config.get("url"))
        self.endpoint = self._normalize_endpoint(config.get("endpoint") or "/api/chat")
        self._endpoint_url = self._build_endpoint_url(self.base_url, self.endpoint)
        self.use_chat_api = "chat" in self.endpoint

        self.default_model = self._coerce_model(config.get("model"), AIModel.QWEN3_8B.value)
        self.allowed_extraction_models = self._normalize_allowed_extraction_models(
            config.get("allowed_extraction_models")
        )
        self.request_timeout = self._coerce_positive_float(config.get("timeout"), 30.0)
        self.max_concurrency = self._coerce_positive_int(
            config.get("max_concurrency"),
            self._env_positive_int("OLLAMA_MAX_CONCURRENCY", 1),
        )
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._client: httpx.AsyncClient | None = None
        self._client_loop: asyncio.AbstractEventLoop | None = None
        self._cache_key = (self.base_url, self.endpoint)

        config_key = (
            self.base_url,
            self.endpoint,
            self.max_concurrency,
            round(self.request_timeout, 3),
            self.default_model,
        )
        if config_key not in _logged_configs:
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
            logger.info(
                "Ollama extraction policy allowed_models=%s",
                ",".join(self.allowed_extraction_models) or "none",
            )
            _logged_configs.add(config_key)

    async def close(self) -> None:
        client = self._client
        self._client = None
        self._client_loop = None
        if client is not None:
            await client.aclose()

    async def _get_client(self, timeout: float | None = None) -> httpx.AsyncClient:
        effective_timeout = timeout if timeout is not None else self.request_timeout
        current_loop = asyncio.get_running_loop()
        client = self._client
        if (
            client is None
            or self._client_loop is not current_loop
            or float(client.timeout.read) != float(effective_timeout)
        ):
            if client is not None:
                await client.aclose()
            self._client = httpx.AsyncClient(timeout=effective_timeout)
            self._client_loop = current_loop
            client = self._client
        return client

    async def discover_models(self, timeout: float = 3.0, force_refresh: bool = False) -> list[str]:
        ttl = self._cache_ttl("OLLAMA_TAGS_CACHE_TTL", 30.0)
        now = time.monotonic()
        cached = _tags_cache.get(self._cache_key)
        if not force_refresh and cached and now - cached[0] <= ttl:
            return list(cached[1])

        client = await self._get_client(timeout=timeout)
        response = await client.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        payload = response.json()
        models = [
            self._coerce_model(item.get("name"), "")
            for item in payload.get("models", [])
            if isinstance(item, dict)
        ]
        models = [model for model in models if model]

        _tags_cache[self._cache_key] = (now, models)
        _health_cache[self._cache_key] = (now, True)
        return list(models)

    async def _available_model_set(self, timeout: float | None = None) -> set[str]:
        models = await self.discover_models(timeout=timeout or self._health_check_timeout)
        return {self._coerce_model(model, "") for model in models if self._coerce_model(model, "")}

    async def validate_model(self, model: AIModel | str) -> bool:
        normalized = self._coerce_model(model, "")
        if not normalized:
            return False
        try:
            available = await self._available_model_set(timeout=self._health_check_timeout)
        except Exception:
            return False
        return normalized in available

    async def health_check(self) -> bool:
        ttl = self._cache_ttl("OLLAMA_HEALTH_CACHE_TTL", 15.0)
        now = time.monotonic()
        cached = _health_cache.get(self._cache_key)
        if cached and now - cached[0] <= ttl:
            return cached[1]

        try:
            await self.discover_models(timeout=self._health_check_timeout)
            _health_cache[self._cache_key] = (now, True)
            return True
        except Exception:
            _health_cache[self._cache_key] = (now, False)
            return False

    async def resolve_model(self, request: AIRequest) -> ModelResolution:
        explicit = self._coerce_model(request.model, "")
        configured = self._coerce_model(self.default_model, AIModel.QWEN3_8B.value)

        try:
            available_models = await self.discover_models(timeout=self._health_check_timeout)
        except Exception as exc:
            logger.warning("No se pudo consultar /api/tags en Ollama: %s", exc)
            available_models = []

        available_set = {self._coerce_model(item, "") for item in available_models if item}

        if request.task == AITask.EXTRACTION:
            return self._resolve_extraction_model(
                explicit=explicit,
                configured=configured,
                available_models=available_models,
                available_set=available_set,
            )

        if explicit:
            if explicit in available_set:
                return ModelResolution(explicit, SelectionReason.EXPLICIT_REQUEST)
            return ModelResolution(
                explicit,
                SelectionReason.EXPLICIT_REQUEST_MISSING,
                error=f"Modelo Ollama no disponible: {explicit}",
            )

        if configured in available_set:
            return ModelResolution(configured, SelectionReason.CONFIGURED_DEFAULT)

        first_available = self._first_available_model(available_models)
        if first_available:
            return ModelResolution(first_available, SelectionReason.FIRST_AVAILABLE)

        if configured:
            return ModelResolution(configured, SelectionReason.CONFIGURED_DEFAULT_FALLBACK)

        return ModelResolution(
            AIModel.QWEN3_8B.value,
            SelectionReason.NO_AVAILABLE_MODELS,
            error=f"No hay modelos Ollama disponibles en {self.base_url}",
        )

    def _resolve_extraction_model(
        self,
        *,
        explicit: str,
        configured: str,
        available_models: list[str],
        available_set: set[str],
    ) -> ModelResolution:
        if explicit:
            if self._is_non_extraction_model(explicit):
                return self._blocked_extraction_model_resolution(
                    explicit=explicit,
                    configured=configured,
                    available_models=available_models,
                    detail=("reason=no_allowed_extraction_model " f"Modelo no permitido para extracción: {explicit}"),
                )
            if explicit in available_set:
                return ModelResolution(explicit, SelectionReason.EXPLICIT_REQUEST)
            return ModelResolution(
                explicit,
                SelectionReason.EXPLICIT_REQUEST_MISSING,
                error=f"Modelo Ollama no disponible: {explicit}",
            )

        if configured and not self._is_non_extraction_model(configured) and configured in available_set:
            return ModelResolution(configured, SelectionReason.CONFIGURED_DEFAULT)

        for candidate in self.allowed_extraction_models:
            normalized = self._coerce_model(candidate, "")
            if not normalized or self._is_non_extraction_model(normalized):
                continue
            if normalized in available_set:
                return ModelResolution(normalized, SelectionReason.ALLOWED_EXTRACTION_MODEL)

        return self._blocked_extraction_model_resolution(
            explicit=explicit,
            configured=configured,
            available_models=available_models,
            detail="reason=no_allowed_extraction_model No allowed extraction model available in Ollama",
        )

    def _blocked_extraction_model_resolution(
        self,
        *,
        explicit: str,
        configured: str,
        available_models: list[str],
        detail: str,
    ) -> ModelResolution:
        selected = explicit or configured or "none"
        logger.warning(
            "extraction_model_selection=blocked reason=no_allowed_extraction_model requested_model=%s configured_model=%s selected_model=%s available_models=%s",
            explicit or "none",
            configured or "none",
            selected,
            available_models,
        )
        return ModelResolution(
            selected,
            SelectionReason.NO_ALLOWED_EXTRACTION_MODEL,
            error=detail,
        )

    async def call(self, request: AIRequest) -> AIResponse:
        start_time = time.perf_counter()
        requested_model = self._coerce_model(request.model, "")
        resolution = await self.resolve_model(request)
        selected_model = resolution.model

        if resolution.error:
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=resolution.error,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
                metadata={
                    "provider": "ollama",
                    "model_requested": requested_model or None,
                    "model_resolved": selected_model,
                    "selection_reason": resolution.reason,
                    "timeout_seconds": self.request_timeout,
                    "timeout_source": self.config.get("timeout_source") or "default",
                },
            )

        logger.info(
            "Ollama request task=%s requested_model=%s resolved_model=%s reason=%s timeout=%.1fs timeout_source=%s",
            request.task.value,
            requested_model or "default",
            selected_model,
            resolution.reason,
            self.request_timeout,
            self.config.get("timeout_source") or "default",
        )

        try:
            prompt = self._prepare_prompt(request)
            payload = self._build_payload(request, prompt, selected_model)

            _call_timeout = (
                float(request.timeout_override)
                if request.timeout_override and request.timeout_override > 0
                else None
            )
            if _call_timeout and _call_timeout != self.request_timeout:
                logger.info(
                    "Ollama timeout_override=%.1fs (default=%.1fs) task=%s model=%s",
                    _call_timeout,
                    self.request_timeout,
                    request.task.value,
                    selected_model,
                )
            async with self._semaphore:
                client = await self._get_client(timeout=_call_timeout)
                response = await client.post(self._endpoint_url, json=payload)
                response.raise_for_status()
                data = response.json()

            content, tokens_used, eval_duration = self._parse_response(data)
            if not content:
                return AIResponse(
                    task=request.task,
                    content="",
                    model=selected_model,
                    error="Respuesta vacÃ­a de Ollama",
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
                    "selection_reason": resolution.reason,
                    "timeout_seconds": self.request_timeout,
                    "timeout_source": self.config.get("timeout_source") or "default",
                    "eval_duration_ns": eval_duration,
                },
            )

        except httpx.ConnectError as exc:
            logger.error("Error conectando a Ollama: %s", exc)
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"No se puede conectar a Ollama: {exc}",
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
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
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            details = ""
            if exc.response is not None:
                try:
                    details = (exc.response.text or "").strip()
                except Exception:
                    details = ""
            logger.warning(
                "Ollama returned HTTP %s for model '%s' at %s. details=%s",
                status,
                selected_model,
                self._endpoint_url,
                details[:300],
            )
            message = f"Ollama HTTP {status}"
            if details:
                message = f"{message}: {details[:300]}"
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=message,
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as exc:
            logger.error("Error en Ollama call: %s", exc, exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"Error Ollama: {exc}",
                processing_time_ms=int((time.perf_counter() - start_time) * 1000),
            )

    def get_default_model(self, task: AITask) -> str:
        return self._coerce_model(self.default_model, AIModel.QWEN3_8B.value)

    def get_supported_models(self) -> list[AIModel]:
        return [AIModel.QWEN3_8B]

    @staticmethod
    def _normalize_base_url(value: Any) -> str:
        raw = str(value or "http://127.0.0.1:11434").strip()
        return raw.rstrip("/")

    @staticmethod
    def _normalize_endpoint(value: Any) -> str:
        raw = str(value or "/api/chat").strip() or "/api/chat"
        if raw.startswith("http"):
            return raw.rstrip("/")
        return raw if raw.startswith("/") else f"/{raw}"

    @staticmethod
    def _build_endpoint_url(base_url: str, endpoint: str) -> str:
        if endpoint.startswith("http"):
            return endpoint.rstrip("/")
        return f"{base_url}{endpoint}"

    @staticmethod
    def _coerce_model(value: Any, default: str) -> str:
        normalized = model_name(value)
        return normalized or default

    @staticmethod
    def _coerce_positive_int(value: Any, default: int) -> int:
        try:
            return max(1, int(str(value).strip()))
        except (TypeError, ValueError, AttributeError):
            return default

    @staticmethod
    def _coerce_positive_float(value: Any, default: float) -> float:
        try:
            parsed = float(str(value).strip())
            return parsed if parsed > 0 else default
        except (TypeError, ValueError, AttributeError):
            return default

    @staticmethod
    def _env_positive_int(name: str, default: int) -> int:
        raw = (os.getenv(name) or "").strip()
        try:
            return max(1, int(raw)) if raw else default
        except ValueError:
            return default

    @staticmethod
    def _cache_ttl(name: str, default: float) -> float:
        raw = (os.getenv(name) or "").strip()
        if not raw:
            return default
        try:
            return max(0.0, float(raw))
        except ValueError:
            return default

    @staticmethod
    def _normalize_allowed_extraction_models(value: Any) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            items = [model_name(item) for item in value]
            normalized = [item for item in items if item]
            return normalized or list(_DEFAULT_ALLOWED_EXTRACTION_MODELS)
        raw = str(value or "").strip()
        if not raw:
            return list(_DEFAULT_ALLOWED_EXTRACTION_MODELS)
        return [item for item in (part.strip() for part in raw.split(",")) if item]

    @staticmethod
    def _is_non_extraction_model(model: str) -> bool:
        normalized = model_name(model).lower()
        if not normalized:
            return True
        base = normalized.split(":", 1)[0]
        blocked_prefixes = (
            "qwen2.5-coder",
            "qwen2.5",
            "minicpm-v",
            "llava",
            "bakllava",
            "moondream",
            "nomic-embed",
            "mxbai-embed",
            "snowflake-arctic-embed",
            "jina-embeddings",
            "all-minilm",
            "bge-",
            "gte-",
            "clip-",
        )
        if base.startswith(blocked_prefixes):
            return True
        blocked_tokens = (
            "vision",
            "multimodal",
            "embed",
            "embedding",
            "adapter",
            "proxy",
            "gateway",
            "openai",
            "azure",
            "anthropic",
            "bedrock",
            "vertex",
            "gemini",
        )
        return any(token in normalized for token in blocked_tokens)

    @staticmethod
    def _first_available_model(models: list[str]) -> str | None:
        for item in models:
            normalized = model_name(item)
            if normalized:
                return normalized
        return None

    def _build_payload(self, request: AIRequest, prompt: str, selected_model: str) -> dict[str, Any]:
        if self.use_chat_api:
            options: dict[str, Any] = {"temperature": request.temperature}
            if request.max_tokens:
                options["num_predict"] = request.max_tokens
            messages = request.messages or [{"role": "user", "content": prompt}]
            return {
                "model": selected_model,
                "messages": messages,
                "stream": False,
                "options": options,
            }

        payload: dict[str, Any] = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["num_predict"] = request.max_tokens
        return payload

    def _parse_response(self, data: dict[str, Any]) -> tuple[str, int | None, Any]:
        if self.use_chat_api:
            content = ((data.get("message") or {}).get("content") or data.get("response") or "").strip()
            tokens_used = data.get("eval_count") or data.get("total_tokens")
            eval_duration = data.get("eval_duration") or data.get("total_duration")
            return content, tokens_used, eval_duration

        content = str(data.get("response") or "").strip()
        tokens_used = data.get("eval_count") or data.get("total_tokens")
        eval_duration = data.get("eval_duration") or data.get("total_duration")
        return content, tokens_used, eval_duration


def model_parameter_size_b(model: str) -> float | None:
    """Best-effort parse of model size from the tag name."""
    normalized = model_name(model).lower()
    match = re.search(r":(\d+(?:\.\d+)?)([bm])(?:$|[^a-z0-9])", normalized)
    if not match:
        return None
    size = float(match.group(1))
    unit = match.group(2)
    return size / 1000.0 if unit == "m" else size

