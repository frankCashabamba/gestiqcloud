"""
OpenAI AI Provider - Fallback provider
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider, model_name

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseAIProvider):
    """
    Proveedor OpenAI para fallback cuando otros no están disponibles.

    Requiere:
        - OPENAI_API_KEY env var
    """

    def __init__(self, config: dict[str, Any]):
        super().__init__("openai", config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url") or os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        self.default_model = AIModel.GPT_35_TURBO
        self.request_timeout = config.get("timeout", 30.0)

        if not self.api_key:
            logger.warning("OpenAI API key no configurada - provider inactivo")

    async def call(self, request: AIRequest) -> AIResponse:
        """Llama a OpenAI API"""
        start_time = time.time()

        try:
            if not self.api_key:
                return AIResponse(
                    task=request.task,
                    content="",
                    model="gpt-3.5-turbo",
                    error="OpenAI API key no configurada",
                    processing_time_ms=int((time.time() - start_time) * 1000),
                )

            prompt = self._prepare_prompt(request)
            model = model_name(request.model) or model_name(self.get_default_model(request.task))

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            messages = request.messages or [
                {"role": "system", "content": self._get_system_prompt(request.task)},
                {"role": "user", "content": prompt},
            ]
            payload = {
                "model": model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 2000,
            }

            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            tokens_used = data.get("usage", {}).get("total_tokens")

            return AIResponse(
                task=request.task,
                content=content,
                model=model,
                tokens_used=tokens_used,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "provider": "openai",
                    "temperature": request.temperature,
                    "input_tokens": data.get("usage", {}).get("prompt_tokens"),
                    "output_tokens": data.get("usage", {}).get("completion_tokens"),
                },
            )

        except Exception as e:
            logger.error(f"Error en OpenAI call: {e}", exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=self.default_model,
                error=f"Error OpenAI: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def health_check(self) -> bool:
        """Verifica conexión a OpenAI"""
        try:
            if not self.api_key:
                return False

            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(f"{self.base_url}/models", headers=headers)
                return response.status_code == 200
        except Exception:
            return False

    def get_default_model(self, task: AITask) -> AIModel:
        """Modelo por defecto"""
        return AIModel.GPT_35_TURBO

    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados por OpenAI"""
        return [
            AIModel.GPT_35_TURBO,
            AIModel.GPT_4_TURBO,
            AIModel.GPT_4O,
        ]
