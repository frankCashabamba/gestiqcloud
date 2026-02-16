"""
Base AI Provider Interface - Abstracción centralizada para múltiples proveedores de IA
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AIModel(str, Enum):
    """Modelos disponibles en cada proveedor"""
    # Ollama
    LLAMA3_1_8B = "llama3.1:8b"
    LLAMA3_1_70B = "llama3.1:70b"
    MISTRAL_7B = "mistral:7b"
    NEURAL_CHAT = "neural-chat:7b"
    
    # OVHCloud / OpenAI
    GPT_4O = "gpt-4o"
    GPT_4_TURBO = "gpt-4-turbo"
    GPT_35_TURBO = "gpt-3.5-turbo"


class AITask(str, Enum):
    """Tipos de tareas soportadas"""
    CLASSIFICATION = "classification"       # Clasificación de documentos
    ANALYSIS = "analysis"                   # Análisis de datos/incidentes
    GENERATION = "generation"               # Generación de contenido (facturas, órdenes)
    SUGGESTION = "suggestion"               # Sugerencias contextuales
    CHAT = "chat"                          # Conversación general
    EXTRACTION = "extraction"               # Extracción de datos


@dataclass
class AIRequest:
    """Estructura estandarizada para requests a IA"""
    task: AITask
    prompt: str
    model: Optional[AIModel] = None
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    context: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.temperature < 0 or self.temperature > 1:
            raise ValueError("temperature debe estar entre 0 y 1")


@dataclass
class AIResponse:
    """Estructura estandarizada para respuestas de IA"""
    task: AITask
    content: str
    model: str
    tokens_used: Optional[int] = None
    confidence: Optional[float] = None
    processing_time_ms: int = 0
    metadata: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    
    @property
    def is_error(self) -> bool:
        return self.error is not None


class BaseAIProvider(ABC):
    """Interfaz base para todos los proveedores de IA"""
    
    def __init__(self, name: str, config: dict[str, Any]):
        self.name = name
        self.config = config
        self._health_check_timeout = config.get("health_check_timeout", 5.0)
        logger.info(f"Inicializando proveedor IA: {name}")
    
    @abstractmethod
    async def call(self, request: AIRequest) -> AIResponse:
        """
        Ejecuta un request a IA y retorna respuesta estandarizada
        
        Args:
            request: AIRequest con prompt, modelo, etc
            
        Returns:
            AIResponse con contenido, tokens, metadatos
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Verifica disponibilidad del proveedor"""
        pass
    
    @abstractmethod
    def get_default_model(self, task: AITask) -> AIModel:
        """Retorna modelo por defecto para una tarea"""
        pass
    
    async def validate_model(self, model: AIModel) -> bool:
        """Valida que el modelo sea soportado"""
        supported = self.get_supported_models()
        return model in supported
    
    @abstractmethod
    def get_supported_models(self) -> list[AIModel]:
        """Lista de modelos soportados por este proveedor"""
        pass
    
    def _prepare_prompt(self, request: AIRequest) -> str:
        """Hook para preparar/validar prompt antes de enviar"""
        if not request.prompt:
            raise ValueError("prompt vacío")
        if len(request.prompt) > self.config.get("max_prompt_length", 10000):
            raise ValueError("prompt demasiado largo")
        return request.prompt
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimación rápida de tokens (1 token ≈ 4 caracteres)"""
        return max(1, len(text) // 4)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
