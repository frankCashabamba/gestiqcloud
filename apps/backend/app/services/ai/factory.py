"""
AI Provider Factory - Crea y gestiona proveedores según configuración
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from app.services.ai.base import AITask, BaseAIProvider
from app.services.ai.providers.ollama import OllamaProvider
from app.services.ai.providers.ovhcloud import OVHCloudProvider
from app.services.ai.providers.openai import OpenAIProvider

logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Factory que gestiona instancias de proveedores IA"""
    
    _instances: dict[str, BaseAIProvider] = {}
    _primary_provider: str = "ollama"
    _fallback_chain: list[str] = ["ollama", "ovhcloud", "openai"]
    
    @classmethod
    def initialize(cls) -> None:
        """Inicializa proveedores basado en configuración de entorno"""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        
        # En producción: OVHCloud primario, OpenAI fallback
        if environment == "production":
            cls._primary_provider = "ovhcloud"
            cls._fallback_chain = ["ovhcloud", "openai"]
            logger.info("Modo producción: OVHCloud primario, OpenAI fallback")
        else:
            # En desarrollo: Ollama primario, OpenAI fallback
            cls._primary_provider = "ollama"
            cls._fallback_chain = ["ollama", "openai"]
            logger.info("Modo desarrollo: Ollama primario, OpenAI fallback")
        
        # Crear instancias
        cls._create_provider("ollama")
        cls._create_provider("ovhcloud")
        cls._create_provider("openai")
    
    @classmethod
    def _create_provider(cls, name: str) -> None:
        """Crea instancia de proveedor específico"""
        config = cls._get_provider_config(name)
        
        try:
            if name == "ollama":
                cls._instances[name] = OllamaProvider(config)
            elif name == "ovhcloud":
                cls._instances[name] = OVHCloudProvider(config)
            elif name == "openai":
                cls._instances[name] = OpenAIProvider(config)
            else:
                logger.warning(f"Proveedor desconocido: {name}")
        except Exception as e:
            logger.error(f"Error creando proveedor {name}: {e}")
    
    @classmethod
    def _get_provider_config(cls, name: str) -> dict[str, Any]:
        """Obtiene configuración del proveedor desde env vars"""
        if name == "ollama":
            return {
                "url": os.getenv("OLLAMA_URL", "http://localhost:11434"),
                "model": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                "timeout": float(os.getenv("OLLAMA_TIMEOUT", "30")),
                "health_check_timeout": float(os.getenv("OLLAMA_HEALTH_TIMEOUT", "5")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }
        
        elif name == "ovhcloud":
            return {
                "url": os.getenv("OVHCLOUD_API_URL", "https://manager.eu.ovhcloud.com/api/v2"),
                "api_key": os.getenv("OVHCLOUD_API_KEY"),
                "api_secret": os.getenv("OVHCLOUD_API_SECRET"),
                "service_name": os.getenv("OVHCLOUD_SERVICE_NAME", "ai"),
                "model": os.getenv("OVHCLOUD_MODEL", "gpt-4o"),
                "timeout": float(os.getenv("OVHCLOUD_TIMEOUT", "60")),
                "health_check_timeout": float(os.getenv("OVHCLOUD_HEALTH_TIMEOUT", "10")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }
        
        elif name == "openai":
            return {
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "timeout": float(os.getenv("OPENAI_TIMEOUT", "30")),
                "health_check_timeout": float(os.getenv("OPENAI_HEALTH_TIMEOUT", "5")),
                "max_prompt_length": int(os.getenv("AI_MAX_PROMPT_LENGTH", "10000")),
            }
        
        return {}
    
    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> BaseAIProvider | None:
        """
        Obtiene proveedor específico o primario
        
        Args:
            name: Nombre del proveedor ("ollama", "ovhcloud", "openai")
            
        Returns:
            Instancia de proveedor o None si no existe
        """
        if not cls._instances:
            cls.initialize()
        
        target = name or cls._primary_provider
        return cls._instances.get(target)
    
    @classmethod
    async def get_available_provider(cls, task: AITask) -> BaseAIProvider | None:
        """
        Obtiene primer proveedor disponible en cadena de fallback
        
        Args:
            task: Tipo de tarea para seleccionar modelo apropiado
            
        Returns:
            Proveedor disponible o None si ninguno funciona
        """
        if not cls._instances:
            cls.initialize()
        
        for provider_name in cls._fallback_chain:
            provider = cls._instances.get(provider_name)
            if provider and await provider.health_check():
                logger.debug(f"Proveedor disponible: {provider_name}")
                return provider
        
        logger.warning("Ningún proveedor IA disponible")
        return None
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """Lista proveedores disponibles"""
        if not cls._instances:
            cls.initialize()
        return list(cls._instances.keys())
    
    @classmethod
    async def health_check_all(cls) -> dict[str, bool]:
        """Verifica salud de todos los proveedores"""
        if not cls._instances:
            cls.initialize()
        
        results = {}
        for name, provider in cls._instances.items():
            try:
                results[name] = await provider.health_check()
            except Exception as e:
                logger.error(f"Error en health_check de {name}: {e}")
                results[name] = False
        
        return results
