"""
Startup initialization para AI Provider Factory
Agregar esto al lifespan de FastAPI en main.py
"""
from __future__ import annotations

import logging

from app.services.ai import AIProviderFactory

logger = logging.getLogger(__name__)


async def initialize_ai_providers() -> None:
    """
    Inicializa todos los proveedores de IA en startup
    
    Llamar desde app.main lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await initialize_ai_providers()
            ...
            yield
            # Shutdown
            ...
    """
    try:
        logger.info("Inicializando proveedores de IA...")
        AIProviderFactory.initialize()
        
        # Verificar salud
        health = await AIProviderFactory.health_check_all()
        
        for provider_name, is_healthy in health.items():
            status = "✅ Disponible" if is_healthy else "❌ No disponible"
            logger.info(f"  {provider_name.upper()}: {status}")
        
        # Determinar estado general
        available = sum(1 for v in health.values() if v)
        if available == 0:
            logger.warning(
                "⚠️  ADVERTENCIA: Ningún proveedor de IA disponible. "
                "Revisa OLLAMA_URL, OVHCLOUD_API_KEY, OPENAI_API_KEY en .env"
            )
        else:
            logger.info(f"✅ {available}/{len(health)} proveedores de IA disponibles")
        
        primary = AIProviderFactory._primary_provider
        logger.info(f"🎯 Proveedor primario: {primary}")
        logger.info(f"🔗 Cadena de fallback: {' → '.join(AIProviderFactory._fallback_chain)}")
        
    except Exception as e:
        logger.error(f"Error inicializando IA: {e}", exc_info=True)
        # No fallar el startup, solo log warning
        # Los providers se inicializan lazy on first use


async def shutdown_ai_providers() -> None:
    """
    Cleanup en shutdown (si es necesario)
    Actualmente no requerido pero disponible para futura extensión
    """
    logger.info("Limpiando proveedores de IA...")
    # Agregar cleanup aquí si es necesario en futuro
