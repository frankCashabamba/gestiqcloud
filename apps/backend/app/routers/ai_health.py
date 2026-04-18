"""
Health check router para proveedores de IA
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.ai import AIProviderFactory

router = APIRouter(prefix="/health/ai", tags=["AI Health"])
logger = logging.getLogger(__name__)


async def _serialize_provider(name: str, provider: Any, *, available: bool) -> dict[str, Any]:
    discovered_models: list[str] = []
    discovery_error: str | None = None

    if hasattr(provider, "discover_models"):
        try:
            discovered_models = list(await provider.discover_models(force_refresh=True))
        except Exception as exc:
            discovery_error = str(exc)

    configured_models = []
    try:
        configured_models = [
            str(m.value if hasattr(m, "value") else m) for m in provider.get_supported_models()
        ]
    except Exception:
        configured_models = []

    config = {
        "base_url": getattr(provider, "base_url", None),
        "endpoint": getattr(provider, "endpoint", None),
        "default_model": str(getattr(provider, "default_model", "") or ""),
        "allowed_extraction_models": list(getattr(provider, "allowed_extraction_models", []) or []),
        "timeout_seconds": getattr(provider, "request_timeout", None),
        "max_concurrency": getattr(provider, "max_concurrency", None),
        "health_check_timeout": getattr(provider, "_health_check_timeout", None),
    }

    return {
        "name": name,
        "available": available,
        "configured": True,
        "models": discovered_models or configured_models,
        "configured_models": configured_models,
        "discovered_models": discovered_models,
        "config": config,
        "discovery_error": discovery_error,
    }


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
    Lista los proveedores IA activos y su configuración efectiva.

    Returns:
        {
            "providers": [
                {
                    "name": "ollama",
                    "available": true,
                    "models": ["<AI_MODEL_QWEN3_8B>", ...],
                    "configured_models": [...],
                    "discovered_models": [...],
                    "config": {...}
                },
            ]
        }
    """
    try:
        if not AIProviderFactory._instances:
            AIProviderFactory.initialize()

        if not AIProviderFactory._instances:
            return {
                "providers": [],
                "primary": None,
                "fallback_chain": [],
                "count": 0,
            }

        health_status = await AIProviderFactory.health_check_all()
        providers_list = []

        for name, provider in AIProviderFactory._instances.items():
            providers_list.append(
                await _serialize_provider(
                    name,
                    provider,
                    available=health_status.get(name, False),
                )
            )

        return {
            "providers": providers_list,
            "primary": AIProviderFactory._primary_provider,
            "fallback_chain": AIProviderFactory._fallback_chain,
            "count": len(providers_list),
        }

    except Exception as e:
        logger.error(f"Error listando providers: {e}")
        raise HTTPException(status_code=500, detail="Error listando providers")
