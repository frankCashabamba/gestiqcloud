"""
Base AI Provider Interface - Abstraccion centralizada para multiples proveedores de IA
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


def messages_to_prompt(messages: list[dict[str, Any]] | None) -> str:
    """Flatten chat messages into a stable text form for cache/logging/recovery."""
    if not messages:
        return ""
    parts: list[str] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "user").strip().lower() or "user"
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        parts.append(f"[{role}]\n{content}")
    return "\n\n".join(parts)


class AIModel(str, Enum):
    """Modelos disponibles — configurable vía AI_MODEL_QWEN3_8B en .env"""

    QWEN3_8B = os.environ.get("AI_MODEL_QWEN3_8B", "qwen3:8b")


def model_name(model: AIModel | str | None) -> str:
    """Normalize model identifiers across Enum/string inputs."""
    if model is None:
        return ""
    if isinstance(model, AIModel):
        return model.value
    return str(model).strip()


class AITask(str, Enum):
    """Tipos de tareas soportadas"""

    CLASSIFICATION = "classification"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    SUGGESTION = "suggestion"
    CHAT = "chat"
    EXTRACTION = "extraction"


@dataclass
class AIRequest:
    """Estructura estandarizada para requests a IA"""

    task: AITask
    prompt: str = ""
    model: AIModel | str | None = None
    temperature: float = 0.3
    max_tokens: int | None = None
    context: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    messages: list[dict[str, Any]] | None = None
    timeout_override: float | None = None  # Por-llamada, anula el timeout del proveedor

    def __post_init__(self):
        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("temperature debe estar entre 0 y 1")
        self.prompt = str(self.prompt or "").strip()
        if self.messages:
            normalized: list[dict[str, Any]] = []
            for item in self.messages:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role") or "user").strip().lower() or "user"
                content = str(item.get("content") or "").strip()
                if not content:
                    continue
                normalized.append({"role": role, "content": content})
            self.messages = normalized or None
        if not self.prompt and self.messages:
            self.prompt = messages_to_prompt(self.messages)
        if not self.prompt:
            raise ValueError("prompt vacio")


@dataclass
class AIResponse:
    """Estructura estandarizada para respuestas de IA"""

    task: AITask
    content: str
    model: str
    tokens_used: int | None = None
    confidence: float | None = None
    processing_time_ms: int = 0
    metadata: dict[str, Any] | None = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


class BaseAIProvider(ABC):
    """Interfaz base para todos los proveedores de IA"""

    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self._health_check_timeout = config.get("health_check_timeout", 5.0)
        logger.info("Inicializando proveedor IA: %s", name)

    @abstractmethod
    async def call(self, request: AIRequest) -> AIResponse:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    @abstractmethod
    def get_default_model(self, task: AITask) -> AIModel | str:
        pass

    async def validate_model(self, model: AIModel | str) -> bool:
        supported = {model_name(item) for item in self.get_supported_models()}
        return model_name(model) in supported

    @abstractmethod
    def get_supported_models(self) -> list[AIModel | str]:
        pass

    def _prepare_prompt(self, request: AIRequest) -> str:
        prompt = request.prompt or messages_to_prompt(request.messages)
        if not prompt:
            raise ValueError("prompt vacio")
        if len(prompt) > self.config.get("max_prompt_length", 10000):
            raise ValueError("prompt demasiado largo")
        return prompt

    def _estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def _get_system_prompt(self, task: AITask) -> str:
        prompts = {
            AITask.CLASSIFICATION: "Eres un experto en clasificacion de documentos empresariales.",
            AITask.ANALYSIS: "Eres un experto en analisis de datos y problemas empresariales.",
            AITask.GENERATION: "Eres un experto en generacion de documentos empresariales precisos.",
            AITask.SUGGESTION: "Eres un asistente experto en sugerir acciones y mejoras.",
            AITask.EXTRACTION: "Eres un experto en extraccion y estructuracion de datos.",
            AITask.CHAT: "Eres un asistente empresarial util, preciso y profesional.",
        }
        return prompts.get(task, "Eres un asistente empresarial util.")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
