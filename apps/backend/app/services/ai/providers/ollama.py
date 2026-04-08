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


# Ollama often degrades under bursty parallel loads. Keep concurrency
# explicit and bounded per base_url instead of freezing one semaphore at import time.
def _ollama_max_concurrency(default: int = 1) -> int:
    raw = (os.getenv("OLLAMA_MAX_CONCURRENCY") or "").strip()
    try:
        return max(1, int(raw)) if raw else default
    except ValueError:
        return default


_ollama_semaphores: dict[tuple[str, int], asyncio.Semaphore] = {}
_logged_concurrency_configs: set[tuple[str, int]] = set()
_tags_cache: dict[str, tuple[float, list[str]]] = {}
_health_cache: dict[str, tuple[float, bool]] = {}


def _coerce_positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(str(value).strip()))
    except (TypeError, ValueError, AttributeError):
        return default


def _coerce_positive_float(value: Any, default: float) -> float:
    try:
        return max(0.0, float(str(value).strip()))
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


def _get_ollama_semaphore(base_url: str, max_concurrency: int) -> asyncio.Semaphore:
    key = (base_url, max_concurrency)
    semaphore = _ollama_semaphores.get(key)
    if semaphore is None:
        semaphore = asyncio.Semaphore(max_concurrency)
        _ollama_semaphores[key] = semaphore
    return semaphore


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
        self.default_model = config.get("model", "qwen2.5:3b")
        # Algunos modelos locales tardan bastante en la primera inferencia (carga a GPU/CPU)
        self.request_timeout = config.get("timeout", 300.0)
        self.max_concurrency = _coerce_positive_int(
            config.get("max_concurrency"),
            _ollama_max_concurrency(),
        )
        self._semaphore = _get_ollama_semaphore(self.base_url, self.max_concurrency)
        config_key = (self.base_url, self.max_concurrency)
        if config_key not in _logged_concurrency_configs:
            logger.info(
                "Ollama concurrency configured base_url=%s max_concurrency=%s endpoint=%s timeout=%.1fs",
                self.base_url,
                self.max_concurrency,
                self.endpoint,
                self.request_timeout,
            )
            _logged_concurrency_configs.add(config_key)

    def _resolve_explicit_extraction_model(self, available: set[str]) -> str | None:
        """Allow forcing a specific extraction model through config or env."""
        override = model_name(os.getenv("OLLAMA_EXTRACTION_MODEL"))
        if override and (not available or override in available):
            return override
        return None

    def _get_available_models(self, timeout: float = 3.0) -> list[str]:
        """Cache /api/tags to avoid repeated round-trips on every request."""
        ttl = _cache_ttl("OLLAMA_TAGS_CACHE_TTL", 30.0)
        now = time.monotonic()
        cached = _tags_cache.get(self.base_url)
        if cached and now - cached[0] <= ttl:
            return list(cached[1])

        resp = httpx.get(f"{self.base_url}/api/tags", timeout=timeout)
        resp.raise_for_status()
        models = [str(model.get("name") or "").strip() for model in resp.json().get("models", [])]
        models = [model for model in models if model]
        _tags_cache[self.base_url] = (now, models)
        _health_cache[self.base_url] = (now, True)
        return list(models)

    async def call(self, request: AIRequest) -> AIResponse:
        """Llama a Ollama API."""
        start_time = time.time()
        selected_model = model_name(request.model) or self.get_default_model(request.task)

        try:
            if not await self.health_check():
                return AIResponse(
                    task=request.task,
                    content="",
                    model=selected_model,
                    error=f"Ollama no disponible en {self.base_url}",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

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

            return AIResponse(
                task=request.task,
                content=content,
                model=selected_model,
                tokens_used=tokens_used or 0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "provider": "ollama",
                    "temperature": request.temperature,
                    "endpoint": self.endpoint,
                    "max_concurrency": self.max_concurrency,
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
                error=f"Ollama timeout ({self.request_timeout:.0f}s). Revisa que el modelo esté cargado o aumenta OLLAMA_TIMEOUT.",
                processing_time_ms=int((time.time() - start_time) * 1000),
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
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error("Error en Ollama call: %s", e, exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=selected_model,
                error=f"Error Ollama: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def health_check(self) -> bool:
        """Verifica que Ollama este disponible."""
        ttl = _cache_ttl("OLLAMA_HEALTH_CACHE_TTL", 15.0)
        now = time.monotonic()
        cached = _health_cache.get(self.base_url)
        if cached and now - cached[0] <= ttl:
            return cached[1]

        try:
            self._get_available_models(timeout=self._health_check_timeout)
            _health_cache[self.base_url] = (now, True)
            return True
        except Exception:
            _health_cache[self.base_url] = (now, False)
            return False

    def _extract_model_candidates(self, available_models: list[str]) -> list[tuple[float, str]]:
        candidates: list[tuple[float, str]] = []
        for model in available_models:
            if _is_non_extraction_model(model):
                continue
            size_b = _model_parameter_size_b(model)
            if size_b is None:
                continue
            candidates.append((size_b, model))
        return candidates

    def _best_extraction_model(self, available_models: list[str] | None = None) -> str | None:
        """Find the safest locally available model for document extraction.

        Preference order:
        1. Highest-capacity model that is still within the configured safety limit.
        2. If nothing fits under the safety limit, the smallest available candidate.
        """
        try:
            available = available_models or self._get_available_models(timeout=3.0)
            candidates = self._extract_model_candidates(available)
            if not candidates:
                return None

            safe_limit_b = _coerce_positive_float(
                os.getenv("OLLAMA_EXTRACTION_MAX_PARAMETER_SIZE_B"),
                3.0,
            )
            safe_candidates = [item for item in candidates if item[0] <= safe_limit_b]
            if safe_candidates:
                best_size_b, best_model = max(safe_candidates, key=lambda item: (item[0], item[1]))
                logger.info(
                    "Using %s for extraction (size=%.1fB within safe limit %.1fB)",
                    best_model,
                    best_size_b,
                    safe_limit_b,
                )
                return best_model

            smallest_size_b, best_model = min(candidates, key=lambda item: (item[0], item[1]))
            logger.info(
                "Using %s for extraction (smallest available; size=%.1fB exceeds safe limit %.1fB)",
                best_model,
                smallest_size_b,
                safe_limit_b,
            )
            return best_model
        except Exception:
            return None

    def get_default_model(self, task: AITask) -> str:
        """Modelo por defecto para Ollama.

        Para tareas de extracción, usa primero un override explícito y luego
        el mejor modelo local que siga dentro del límite seguro configurado.
        Para otras tareas, usa el modelo configurado por entorno.
        """
        configured = model_name(self.default_model)
        if task == AITask.EXTRACTION:
            try:
                available_models = self._get_available_models(timeout=3.0)
            except Exception:
                available_models = []
            available_set = set(available_models)

            explicit = self._resolve_explicit_extraction_model(available_set)
            if explicit:
                return explicit

            if configured and configured in available_set:
                configured_size_b = _model_parameter_size_b(configured)
                safe_limit_b = _coerce_positive_float(
                    os.getenv("OLLAMA_EXTRACTION_MAX_PARAMETER_SIZE_B"),
                    3.0,
                )
                if configured_size_b is None or configured_size_b <= safe_limit_b:
                    logger.info(
                        "Using configured Ollama model %s for extraction (size=%s)",
                        configured,
                        f"{configured_size_b:.1f}B" if configured_size_b is not None else "unknown",
                    )
                    return configured

            extraction_model = self._best_extraction_model(available_models)
            if extraction_model:
                return extraction_model
        if configured:
            return configured
        return AIModel.QWEN2_5_3B.value

    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados historicamente por esta app para Ollama."""
        return [
            AIModel.QWEN2_5_3B,
            AIModel.LLAMA3_1_8B,
            AIModel.LLAMA3_1_70B,
            AIModel.MISTRAL_7B,
            AIModel.NEURAL_CHAT,
        ]
