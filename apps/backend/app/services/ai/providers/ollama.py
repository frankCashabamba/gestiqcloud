"""
Ollama AI Provider - Local LLM via Ollama
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider, model_name

logger = logging.getLogger(__name__)

# Ollama processes one request at a time; serialize calls so queued
# requests wait in Python instead of hitting httpx timeouts.
_ollama_semaphore = asyncio.Semaphore(1)


class OllamaProvider(BaseAIProvider):
    """
    Proveedor local Ollama para desarrollo/testing.
    Requiere Ollama corriendo localmente en puerto 11434.
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("ollama", config)
        self.base_url = config.get("url", "http://localhost:11434")
        self.default_model = config.get("model", "llama3.1:8b")
        self.request_timeout = config.get("timeout", 120.0)

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
            payload = {
                "model": selected_model,
                "prompt": prompt,
                "stream": False,
                "temperature": request.temperature,
            }

            if request.max_tokens:
                payload["num_predict"] = request.max_tokens

            async with _ollama_semaphore:
                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    response = await client.post(f"{self.base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()

            return AIResponse(
                task=request.task,
                content=data.get("response", "").strip(),
                model=selected_model,
                tokens_used=data.get("eval_count", 0),
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "provider": "ollama",
                    "temperature": request.temperature,
                    "eval_duration_ns": data.get("eval_duration"),
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
                f"{self.base_url}/api/generate",
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
        try:
            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def get_default_model(self, task: AITask) -> str:
        """Modelo por defecto para Ollama.

        Priorizamos el modelo configurado por entorno porque la instalacion
        de modelos varia por maquina.
        """
        configured = model_name(self.default_model)
        if configured:
            return configured
        return AIModel.LLAMA3_1_8B.value

    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados historicamente por esta app para Ollama."""
        return [
            AIModel.LLAMA3_1_8B,
            AIModel.LLAMA3_1_70B,
            AIModel.MISTRAL_7B,
            AIModel.NEURAL_CHAT,
        ]
