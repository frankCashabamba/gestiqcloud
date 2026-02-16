"""
Endpoint GET /imports/ai/health para healthcheck del sistema IA
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.access_guard import with_access_claims
from app.services.ai.factory import AIProviderFactory

logger = logging.getLogger("app.imports.ai.health")

router = APIRouter(
    prefix="/ai",
    tags=["Imports AI Health"],
    dependencies=[Depends(with_access_claims)],
)


@router.get("/health")
async def ai_health(request: Request) -> dict[str, Any]:
    """
    Healthcheck del sistema IA.
    
    Retorna:
    - status: "healthy", "degraded", o "unavailable"
    - provider: nombre del proveedor actual
    - available_providers: lista de providers disponibles
    - latency_ms: latencia del proveedor actual (opcional)
    
    Ejemplo de respuesta:
    ```json
    {
      "status": "healthy",
      "provider": "ovhcloud",
      "available_providers": ["ovhcloud", "ollama", "local"],
      "latency_ms": 125
    }
    ```
    """
    try:
        # Obtener proveedor disponible
        provider = await AIProviderFactory.get_available_provider(None)
        
        if not provider:
            return {
                "status": "unavailable",
                "provider": None,
                "available_providers": [],
                "latency_ms": None,
            }
        
        # Health check del proveedor
        start_time = time.time()
        is_healthy = await provider.health_check()
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Obtener lista de providers disponibles
        all_providers = AIProviderFactory.get_all_providers()
        available_names = [p.name for p in all_providers if p is not None]
        
        return {
            "status": "healthy" if is_healthy else "degraded",
            "provider": provider.name,
            "available_providers": available_names,
            "latency_ms": latency_ms,
        }
    
    except Exception as e:
        logger.error(f"Error checking AI health: {e}", exc_info=True)
        return {
            "status": "unavailable",
            "provider": None,
            "available_providers": [],
            "error": str(e),
        }


@router.get("/status")
async def ai_status(request: Request) -> dict[str, Any]:
    """
    Estado detallado del sistema IA.
    
    Retorna información sobre:
    - Provider actual
    - Modelos soportados
    - Configuración
    - Metrics (requests, costs, etc)
    """
    try:
        provider = await AIProviderFactory.get_available_provider(None)
        
        if not provider:
            return {
                "status": "unavailable",
                "provider": None,
            }
        
        # Obtener telemetría del provider
        telemetry = provider.get_telemetry() if hasattr(provider, 'get_telemetry') else {}
        
        return {
            "status": "available",
            "provider": provider.name,
            "model": getattr(provider, 'default_model', 'unknown'),
            "supported_models": [m.value for m in provider.get_supported_models()] if hasattr(provider, 'get_supported_models') else [],
            "telemetry": telemetry,
        }
    
    except Exception as e:
        logger.error(f"Error getting AI status: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }


@router.get("/providers")
async def ai_providers(request: Request) -> dict[str, Any]:
    """
    Lista de todos los providers IA disponibles en el sistema.
    
    Retorna información sobre cada provider:
    - name: nombre del provider
    - healthy: si está disponible
    - latency_ms: latencia del último check
    """
    try:
        all_providers = AIProviderFactory.get_all_providers()
        
        providers_info = []
        for provider in all_providers:
            if provider is None:
                continue
            
            try:
                start_time = time.time()
                is_healthy = await provider.health_check()
                latency_ms = int((time.time() - start_time) * 1000)
                
                providers_info.append({
                    "name": provider.name,
                    "healthy": is_healthy,
                    "latency_ms": latency_ms,
                })
            except Exception as e:
                logger.debug(f"Error checking {provider.name}: {e}")
                providers_info.append({
                    "name": provider.name,
                    "healthy": False,
                    "error": str(e),
                })
        
        return {
            "providers": providers_info,
            "total": len(providers_info),
        }
    
    except Exception as e:
        logger.error(f"Error getting providers: {e}", exc_info=True)
        return {
            "error": str(e),
            "providers": [],
        }
