"""
Health check router para proveedores de IA
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.ai import AIProviderFactory

router = APIRouter(prefix="/api/v1/health/ai", tags=["AI Health"])
logger = logging.getLogger(__name__)


@router.get("", response_model=dict[str, Any])
async def ai_health_check():
    """
    Verifica disponibilidad de todos los proveedores de IA
    
    Returns:
        {
            "status": "healthy|degraded|unavailable",
            "primary_provider": str,
            "providers": {
                "ollama": true/false,
                "ovhcloud": true/false,
                "openai": true/false
            }
        }
    """
    try:
        # Inicializar si es necesario
        if not AIProviderFactory._instances:
            AIProviderFactory.initialize()
        
        # Verificar todos
        health_status = await AIProviderFactory.health_check_all()
        
        # Determinar estado general
        available = sum(1 for v in health_status.values() if v)
        if available == 0:
            status = "unavailable"
        elif available == len(health_status):
            status = "healthy"
        else:
            status = "degraded"
        
        # Obtener providers activos
        providers = {}
        for name, provider in AIProviderFactory._instances.items():
            providers[name] = health_status.get(name, False)
        
        return {
            "status": status,
            "primary_provider": AIProviderFactory._primary_provider,
            "providers": providers,
            "total_providers": len(providers),
            "available_providers": available,
        }
    
    except Exception as e:
        logger.error(f"Error en AI health check: {e}")
        raise HTTPException(status_code=500, detail="Error en health check de IA")


@router.get("/providers", response_model=dict[str, Any])
async def list_ai_providers():
    """
    Lista todos los proveedores configurados y disponibles
    
    Returns:
        {
            "providers": [
                {
                    "name": "ollama",
                    "available": true,
                    "models": ["llama3.1:8b", ...],
                    "config": {...}
                },
                ...
            ]
        }
    """
    try:
        if not AIProviderFactory._instances:
            AIProviderFactory.initialize()
        
        providers_list = []
        health_status = await AIProviderFactory.health_check_all()
        
        for name, provider in AIProviderFactory._instances.items():
            provider_info = {
                "name": name,
                "available": health_status.get(name, False),
                "supported_models": [m.value for m in provider.get_supported_models()],
                "default_model": provider.get_default_model(None).__str__() if hasattr(provider, 'default_model') else "unknown",
            }
            providers_list.append(provider_info)
        
        return {
            "providers": providers_list,
            "primary": AIProviderFactory._primary_provider,
            "fallback_chain": AIProviderFactory._fallback_chain,
        }
    
    except Exception as e:
        logger.error(f"Error listando providers: {e}")
        raise HTTPException(status_code=500, detail="Error listando providers")
