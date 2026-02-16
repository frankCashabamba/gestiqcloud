"""
OVHCloud AI Provider - Producción LLM via OVHCloud Manager
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from app.services.ai.base import AIModel, AIRequest, AIResponse, AITask, BaseAIProvider

logger = logging.getLogger(__name__)


class OVHCloudProvider(BaseAIProvider):
    """
    Proveedor OVHCloud para producción.
    Usa OVHCloud Manager AI API (manager.eu.ovhcloud.com)
    
    Requiere:
        - OVHCloud_API_KEY env var
        - OVHCloud_API_SECRET env var
        - Acceso a OVHCloud AI APIs
    """
    
    def __init__(self, config: dict[str, Any]):
        super().__init__("ovhcloud", config)
        self.base_url = config.get("url", "https://manager.eu.ovhcloud.com/api/v2")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")
        self.service_name = config.get("service_name", "ai")
        self.default_model = config.get("model", AIModel.GPT_4O)
        self.request_timeout = config.get("timeout", 60.0)
        
        if not self.api_key or not self.api_secret:
            logger.warning("OVHCloud API credentials no configuradas - provider inactivo")
    
    async def call(self, request: AIRequest) -> AIResponse:
        """Llama a OVHCloud AI API"""
        start_time = time.time()
        
        try:
            if not self.api_key or not self.api_secret:
                return AIResponse(
                    task=request.task,
                    content="",
                    model="gpt-4o",
                    error="OVHCloud API credentials no configuradas",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            if not await self.health_check():
                return AIResponse(
                    task=request.task,
                    content="",
                    model=self.default_model,
                    error="OVHCloud API no disponible",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )
            
            prompt = self._prepare_prompt(request)
            model = request.model or self.get_default_model(request.task)
            
            # Construir request según OVHCloud API spec
            headers = self._build_headers()
            payload = {
                "model": str(model),
                "messages": [
                    {
                        "role": "system",
                        "content": self._get_system_prompt(request.task)
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 2000,
            }
            
            # Llamar OVHCloud
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                response = await client.post(
                    f"{self.base_url}/ai/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
            
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            tokens_used = data.get("usage", {}).get("total_tokens")
            
            return AIResponse(
                task=request.task,
                content=content,
                model=str(model),
                tokens_used=tokens_used,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "provider": "ovhcloud",
                    "temperature": request.temperature,
                    "input_tokens": data.get("usage", {}).get("prompt_tokens"),
                    "output_tokens": data.get("usage", {}).get("completion_tokens"),
                }
            )
            
        except httpx.HTTPError as e:
            logger.error(f"Error OVHCloud API: {e}")
            return AIResponse(
                task=request.task,
                content="",
                model=self.default_model,
                error=f"OVHCloud API error: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Error en OVHCloud call: {e}", exc_info=True)
            return AIResponse(
                task=request.task,
                content="",
                model=self.default_model,
                error=f"Error OVHCloud: {str(e)}",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def health_check(self) -> bool:
        """Verifica conexión a OVHCloud API"""
        try:
            if not self.api_key or not self.api_secret:
                return False
            
            headers = self._build_headers()
            async with httpx.AsyncClient(timeout=self._health_check_timeout) as client:
                response = await client.get(
                    f"{self.base_url}/ai/health",
                    headers=headers
                )
                return response.status_code == 200
        except Exception:
            return False
    
    def get_default_model(self, task: AITask) -> AIModel:
        """Modelo por defecto según tarea"""
        if task == AITask.ANALYSIS or task == AITask.GENERATION:
            return AIModel.GPT_4O
        elif task == AITask.CLASSIFICATION:
            return AIModel.GPT_35_TURBO
        else:
            return AIModel(self.default_model)
    
    def get_supported_models(self) -> list[AIModel]:
        """Modelos soportados por OVHCloud"""
        return [
            AIModel.GPT_4O,
            AIModel.GPT_4_TURBO,
            AIModel.GPT_35_TURBO,
        ]
    
    def _build_headers(self) -> dict[str, str]:
        """Construye headers con autenticación OVHCloud"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-OVH-Secret": self.api_secret,
            "Content-Type": "application/json",
        }
    
    def _get_system_prompt(self, task: AITask) -> str:
        """System prompt por defecto según tarea"""
        prompts = {
            AITask.CLASSIFICATION: "Eres un experto en clasificación de documentos empresariales.",
            AITask.ANALYSIS: "Eres un experto en análisis de datos y problemas empresariales.",
            AITask.GENERATION: "Eres un experto en generación de documentos empresariales precisos.",
            AITask.SUGGESTION: "Eres un asistente experto en sugerir acciones y mejoras.",
            AITask.EXTRACTION: "Eres un experto en extracción y estructuración de datos.",
            AITask.CHAT: "Eres un asistente empresarial útil, preciso y profesional.",
        }
        return prompts.get(task, "Eres un asistente empresarial útil.")
