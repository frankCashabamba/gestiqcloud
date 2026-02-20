"""
Ollama AI Provider - Local LLM via Ollama
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseAIProvider):
    """
    Proveedor local Ollama para desarrollo/testing.
    Requiere Ollama corriendo localmente en puerto 11434

    Instalación:
        curl https://ollama.ai/install.sh | sh
        ollama pull llama3.1:8b
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("ollama", config)
        self.base_url = config.get("url", "http://localhost:11434")
        self.default_model = config.get("model", "llama3.1:8b")
        self.request_timeout = config.get("timeout", 30.0)

    async def call(self, request: AIRequest) -> AIResponse:
        """Llama a Ollama API"""
        start_time = time.time()

        try:
            # Validar y preparar
            if not await self.health_check():
                return AIResponse(
                    task=request.task,
                    content="",
                    model=self.default_model,
                    error=f"Ollama no disponible en {self.base_url}",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            prompt = self._prepare_prompt(request)
            model = request.model or self.get_default_model(request.task)

            # Construir payload
            payload = {
                "model": str(model),
                "prompt": prompt,
                "stream": False,
                "temperature": request.temperature,
            }

            if request.max_tokens:
                payload["num_predict"] = request.max_tokens

            # Llamar Ollama
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()

            content = data.get("response", "").strip()
            tokens = data.get("eval_count", 0)

            return AIResponse(
                task=request.task,
                content=content,
                model=str(model),
                tokens_used=tokens,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "provider": "ollama",
                    "temperature": request.temperature,
                    "eval_duration_ns": data.get("eval_duration"),
                },
            )

        except httpx.ConnectError as e:
            logger.error(f"Error conectando a Ollama: {e}")
            return AIResponse(
                task=request.task,
                content="",
                model=self.default_model,
                error=f"No se puede conectar a Ollama: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error(f"Error en Ollama call: {e}", exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=self.default_model,
                error=f"Error Ollama: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def health_check(self) -> bool:
        """Verifica que Ollama esté disponible"""
        try:
            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def get_default_model(self, task: AITask) -> AIModel:
        """Modelo por defecto según tarea"""
        if task == AITask.ANALYSIS:
            return AIModel.LLAMA3_1_70B
        elif task == AITask.GENERATION:
            return AIModel.LLAMA3_1_8B
        elif task == AITask.CLASSIFICATION:
            return AIModel.MISTRAL_7B
        else:
            return AIModel(self.default_model)

    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados por Ollama"""
        return [
            AIModel.LLAMA3_1_8B,
            AIModel.LLAMA3_1_70B,
            AIModel.MISTRAL_7B,
            AIModel.NEURAL_CHAT,
        ]
