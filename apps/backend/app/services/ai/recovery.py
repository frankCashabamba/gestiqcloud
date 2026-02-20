"""
Sistema de recuperación y corrección automática de errores de IA
Intenta solucionar problemas automáticamente
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.services.ai.base import AIRequest, AIResponse
from app.services.ai.factory import AIProviderFactory
from app.services.ai.logging import AILogger

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """Base para estrategias de recuperación"""

    def __init__(self, name: str):
        self.name = name

    async def execute(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """
        Intenta recuperarse del error

        Returns:
            AIResponse si tuvo éxito, None si debe intentar siguiente estrategia
        """
        raise NotImplementedError


class RetryStrategy(ErrorRecoveryStrategy):
    """Reintentar con backoff exponencial"""

    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0):
        super().__init__("retry")
        self.max_retries = max_retries
        self.initial_delay = initial_delay

    async def execute(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """Reintentar con backoff"""
        for attempt in range(self.max_retries):
            try:
                # Esperar exponencialmente
                delay = self.initial_delay * (2**attempt)
                await asyncio.sleep(delay)

                # Obtener proveedor disponible
                provider = await AIProviderFactory.get_available_provider(request.task)
                if not provider:
                    logger.warning(f"No providers available for retry {attempt + 1}")
                    continue

                logger.info(f"Retry {attempt + 1}/{self.max_retries} con {provider.name}")

                # Llamar
                start = time.time()
                response = await provider.call(request)
                recovery_time = int((time.time() - start) * 1000)

                if not response.is_error:
                    # Registrar recuperación exitosa
                    AILogger.log_recovery_attempt(
                        db,
                        request_id,
                        self.name,
                        f"Reintentado en intento {attempt + 1}",
                        success=True,
                        recovery_time_ms=recovery_time,
                        result={"provider": provider.name, "attempt": attempt + 1},
                    )
                    return response

            except Exception as e:
                logger.debug(f"Retry {attempt + 1} failed: {e}")
                continue

        return None


class FallbackStrategy(ErrorRecoveryStrategy):
    """Cambiar a diferente proveedor"""

    def __init__(self):
        super().__init__("fallback")

    async def execute(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """Intentar con siguiente proveedor en cadena"""
        try:
            for provider_name in AIProviderFactory._fallback_chain:
                try:
                    provider = AIProviderFactory.get_provider(provider_name)
                    if not provider:
                        continue

                    # Verificar que esté disponible
                    if not await provider.health_check():
                        logger.debug(f"Provider {provider_name} not healthy")
                        continue

                    logger.info(f"Fallback a proveedor: {provider_name}")

                    # Llamar
                    start = time.time()
                    response = await provider.call(request)
                    recovery_time = int((time.time() - start) * 1000)

                    if not response.is_error:
                        AILogger.log_recovery_attempt(
                            db,
                            request_id,
                            self.name,
                            f"Fallback a {provider_name}",
                            success=True,
                            recovery_time_ms=recovery_time,
                            result={"provider": provider_name},
                        )
                        return response

                except Exception as e:
                    logger.debug(f"Fallback a {provider_name} falló: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error en FallbackStrategy: {e}")

        return None


class SimplifyStrategy(ErrorRecoveryStrategy):
    """Simplificar el prompt y reintentar"""

    def __init__(self):
        super().__init__("simplify")

    async def execute(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """Intentar con prompt simplificado"""
        try:
            # Detectar si fue truncado
            if len(request.prompt) > 5000:
                logger.info("Simplificando prompt (muy largo)")

                # Truncar a 3000 caracteres
                simplified_prompt = request.prompt[:3000] + "\n[TRUNCADO]"

                # Crear nuevo request
                simplified_request = AIRequest(
                    task=request.task,
                    prompt=simplified_prompt,
                    temperature=max(0.1, request.temperature - 0.1),  # Menos creativo
                    max_tokens=request.max_tokens or 1000,
                )

                # Llamar con prompt simplificado
                provider = await AIProviderFactory.get_available_provider(request.task)
                if provider:
                    start = time.time()
                    response = await provider.call(simplified_request)
                    recovery_time = int((time.time() - start) * 1000)

                    if not response.is_error:
                        AILogger.log_recovery_attempt(
                            db,
                            request_id,
                            self.name,
                            "Prompt simplificado",
                            success=True,
                            recovery_time_ms=recovery_time,
                            result={"simplified": True},
                        )
                        return response

        except Exception as e:
            logger.debug(f"Simplify strategy failed: {e}")

        return None


class CacheStrategy(ErrorRecoveryStrategy):
    """Usar respuesta en caché si disponible"""

    def __init__(self):
        super().__init__("cache")

    async def execute(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """
        Buscar en cache (futuro)
        Por ahora es placeholder
        """
        # TODO: Implementar cache en Redis
        return None


class AIRecoveryManager:
    """Orquestador de estrategias de recuperación"""

    def __init__(self):
        self.strategies: list[ErrorRecoveryStrategy] = [
            RetryStrategy(max_retries=2, initial_delay=0.5),
            SimplifyStrategy(),
            FallbackStrategy(),
            CacheStrategy(),
        ]

    async def recover(
        self,
        request: AIRequest,
        db: Session,
        request_id: str,
        original_error: str,
    ) -> AIResponse | None:
        """
        Ejecuta estrategias de recuperación en orden

        Returns:
            AIResponse si se recuperó, None si no
        """
        logger.warning(
            f"Iniciando recuperación de error: {request_id}\nError original: {original_error}"
        )

        for strategy in self.strategies:
            try:
                logger.info(f"Intentando estrategia: {strategy.name}")
                response = await strategy.execute(request, db, request_id, original_error)

                if response and not response.is_error:
                    logger.info(f"✅ Recuperación exitosa con estrategia: {strategy.name}")
                    return response

            except Exception as e:
                logger.error(
                    f"Error en estrategia {strategy.name}: {e}",
                    exc_info=True,
                )
                continue

        logger.error(f"❌ No se pudo recuperar de error: {request_id}")
        return None

    async def suggest_fix(
        self,
        db: Session,
        error_code: str,
        error_message: str,
    ) -> dict[str, Any]:
        """
        Sugiere fixes para un error
        """
        fixes = {}

        # Análisis de error conocido
        if "connection" in error_message.lower():
            fixes = {
                "type": "connectivity",
                "suggestions": [
                    "Verificar conexión de red",
                    "Verificar que Ollama/OVHCloud está corriendo",
                    "Revisar firewall/proxy",
                    "Aumentar timeout",
                ],
            }

        elif "timeout" in error_message.lower():
            fixes = {
                "type": "timeout",
                "suggestions": [
                    "Aumentar timeout",
                    "Reducir max_tokens",
                    "Simplificar prompt",
                    "Usar modelo más rápido (8B vs 70B)",
                ],
            }

        elif "memory" in error_message.lower() or "out of" in error_message.lower():
            fixes = {
                "type": "resource",
                "suggestions": [
                    "Aumentar RAM disponible",
                    "Usar modelo más pequeño",
                    "Reducir max_tokens",
                    "Limpiar cache del modelo",
                ],
            }

        elif "unauthorized" in error_message.lower() or "401" in error_message:
            fixes = {
                "type": "auth",
                "suggestions": [
                    "Verificar API key/secret",
                    "Verificar credenciales OVHCloud",
                    "Rotar keys si es necesario",
                ],
            }

        elif "invalid" in error_message.lower() or "parse" in error_message.lower():
            fixes = {
                "type": "parsing",
                "suggestions": [
                    "Respuesta IA malformada",
                    "Intentar simplificar prompt",
                    "Cambiar temperatura a valor más bajo",
                    "Intentar con diferentes modelo",
                ],
            }

        else:
            fixes = {
                "type": "unknown",
                "suggestions": [
                    "Revisar logs completos",
                    "Intentar reiniciar servicio",
                    "Contactar soporte",
                ],
                "error": error_message,
            }

        return fixes


# Instancia global
recovery_manager = AIRecoveryManager()
