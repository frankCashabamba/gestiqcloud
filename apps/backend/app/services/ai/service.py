"""
Servicio Unificado de IA - API consistente para todas las características
Con logging automático, análisis de errores y recuperación
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache import CacheTTL, build_cache_key, cache_get, cache_set
from app.services.ai.base import AIRequest, AIResponse, AITask
from app.services.ai.factory import AIProviderFactory
from app.services.ai.logging import AILogger
from app.services.ai.recovery import recovery_manager

logger = logging.getLogger(__name__)

_OPENAI_COOLDOWN_KEY = build_cache_key("global", "ai", "openai_rate_limit")
_OPENAI_COOLDOWN_SECONDS = 30 * 60


def _cache_fingerprint_for_request(request: AIRequest) -> str:
    key_payload = {
        "task": str(request.task),
        "prompt": request.prompt,
        "messages": request.messages or [],
        "model": str(request.model or ""),
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "context": request.context or {},
    }
    return hashlib.md5(
        json.dumps(key_payload, sort_keys=True, default=str).encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


def _cache_key_for_request(tenant_id: str | None, request: AIRequest) -> str:
    cache_tenant = str(tenant_id or "global")
    return build_cache_key(cache_tenant, "ai_recovery", _cache_fingerprint_for_request(request))


async def _load_response_from_cache(
    tenant_id: str | None,
    request: AIRequest,
) -> AIResponse | None:
    cached = await cache_get(_cache_key_for_request(tenant_id, request))
    if not isinstance(cached, dict) or not cached.get("content"):
        return None
    return AIResponse(
        task=request.task,
        content=str(cached.get("content") or ""),
        model=str(cached.get("model") or "cache"),
        tokens_used=cached.get("tokens_used"),
        confidence=cached.get("confidence"),
        processing_time_ms=0,
        metadata={
            **(cached.get("metadata") or {}),
            "source": "redis_cache",
            "cache_ttl": int(CacheTTL.MEDIUM),
        },
    )


async def _store_response_in_cache(
    tenant_id: str | None, request: AIRequest, response: AIResponse
) -> None:
    if response.is_error or not response.content:
        return
    await cache_set(
        _cache_key_for_request(tenant_id, request),
        {
            "content": response.content,
            "model": response.model,
            "tokens_used": response.tokens_used,
            "confidence": response.confidence,
            "metadata": response.metadata or {},
        },
        ttl=CacheTTL.MEDIUM,
    )


def _get_ai_fallback_policy(request: AIRequest) -> dict[str, Any] | None:
    context = request.context
    if not isinstance(context, dict):
        return None

    policy = context.get("ai_fallback_policy")
    return policy if isinstance(policy, dict) else None


def _policy_bool(policy: dict[str, Any], key: str, default: bool = False) -> bool:
    value = policy.get(key, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _policy_int(policy: dict[str, Any], key: str, default: int) -> int:
    try:
        return max(0, int(float(policy.get(key, default))))
    except (TypeError, ValueError):
        return default


def _policy_float(policy: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(policy.get(key, default))
    except (TypeError, ValueError):
        return default


async def _openai_cooldown_active() -> bool:
    payload = await cache_get(_OPENAI_COOLDOWN_KEY)
    if not isinstance(payload, dict):
        return False
    try:
        until = int(float(payload.get("until") or 0))
    except (TypeError, ValueError):
        return False
    return until > int(time.time())


async def _register_openai_cooldown(
    *, reason: str, seconds: int = _OPENAI_COOLDOWN_SECONDS
) -> None:
    try:
        now = int(time.time())
        await cache_set(
            _OPENAI_COOLDOWN_KEY,
            {"until": now + max(60, int(seconds)), "reason": reason},
            ttl=max(60, int(seconds)),
        )
    except Exception:
        logger.debug("No se pudo registrar cooldown de OpenAI", exc_info=True)


async def _call_openai_fallback(
    request: AIRequest,
    *,
    current_provider_name: str,
) -> AIResponse | None:
    if await _openai_cooldown_active():
        logger.info(
            "OpenAI fallback skipped for %s: cooldown activo por rate limit", current_provider_name
        )
        return None

    openai_provider = AIProviderFactory.get_provider("openai")
    if not openai_provider:
        return None

    if not await openai_provider.health_check():
        logger.info(
            "OpenAI fallback skipped for %s: provider unavailable",
            current_provider_name,
        )
        return None

    logger.info("Escalating %s request to OpenAI fallback", current_provider_name)
    try:
        response = await openai_provider.call(request)
    except Exception as exc:
        logger.warning("OpenAI fallback failed after %s: %s", current_provider_name, exc)
        if "429" in str(exc) or "rate limit" in str(exc).lower():
            await _register_openai_cooldown(reason=str(exc))
        return None

    if response.is_error:
        logger.warning(
            "OpenAI fallback returned error after %s: %s",
            current_provider_name,
            (response.error or "")[:200],
        )
        if "429" in (response.error or "") or "rate limit" in (response.error or "").lower():
            await _register_openai_cooldown(reason=response.error or "openai rate limit")
        return None

    return response


async def _should_route_to_openai_before_call(
    request: AIRequest,
    *,
    current_provider_name: str,
) -> bool:
    if current_provider_name != "ollama":
        return False

    fallback_policy = _get_ai_fallback_policy(request)
    if not fallback_policy or not _policy_bool(fallback_policy, "enabled", True):
        return False

    if await _openai_cooldown_active():
        return False

    if not (
        _policy_bool(fallback_policy, "allow_on_complex", True)
        or _policy_bool(fallback_policy, "allow_on_slow", True)
    ):
        return False

    complexity_score = _policy_float(fallback_policy, "complexity_score", 0.0)
    complexity_threshold = _policy_float(fallback_policy, "complexity_threshold", 0.72)
    if complexity_score < complexity_threshold:
        return False

    return True


class AIService:
    """Servicio unificado de IA con fallback automático y recuperación de errores"""

    @staticmethod
    async def query(
        task: AITask,
        prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int | None = None,
        context: dict[str, Any] | None = None,
        provider: str | None = None,
        db: Session | None = None,
        tenant_id: str | None = None,
        module: str | None = None,
        user_id: str | None = None,
        enable_recovery: bool = True,
        model: str | None = None,
        messages: list[dict[str, Any]] | None = None,
    ) -> AIResponse:
        """
        Consulta IA con proveedor automático o específico
        Con logging automático y recuperación de errores

        Args:
            task: Tipo de tarea (classification, analysis, etc)
            prompt: Prompt para enviar a IA
            temperature: Control de creatividad (0-1)
            max_tokens: Límite de tokens en respuesta
            context: Contexto adicional para la tarea
            provider: Proveedor específico ("ollama", "ovhcloud", "openai") o None para auto
            db: Sesión de BD para logging (opcional)
            tenant_id: ID del tenant (para auditoría)
            module: Módulo que solicita (copilot, imports, etc)
            user_id: ID del usuario (para auditoría)
            enable_recovery: Intentar recuperarse de errores automáticamente

        Returns:
            AIResponse con contenido y metadatos
        """
        # Crear request
        request = AIRequest(
            task=task,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            context=context,
            model=model or None,
            messages=messages,
        )

        cached_response = await _load_response_from_cache(tenant_id, request)

        # Generar ID para tracking
        request_id = None
        if db:
            try:
                provider_name = provider or ("cache" if cached_response else "auto")
                provider_model = "cache" if cached_response else "unknown"
                if not cached_response:
                    ai_provider = await AIProviderFactory.get_available_provider(task)
                    provider_model = ai_provider.default_model if ai_provider else "unknown"
                request_id = AILogger.log_request(
                    db,
                    request,
                    provider_name=provider_name,
                    provider_model=str(provider_model),
                    tenant_id=tenant_id,
                    module=module,
                    user_id=user_id,
                )
            except Exception as e:
                logger.debug(f"Error logging request: {e}")

        if cached_response:
            if db and request_id:
                AILogger.log_response(db, request_id, cached_response)
            logger.debug(f"IA query ({task}): redis_cache hit")
            return cached_response

        # Obtener proveedor
        if provider:
            ai_provider = AIProviderFactory.get_provider(provider)
            if not ai_provider:
                logger.warning(f"Proveedor {provider} no disponible, usando fallback")
                ai_provider = await AIProviderFactory.get_available_provider(task)
        else:
            ai_provider = await AIProviderFactory.get_available_provider(task)

        if not ai_provider:
            response = AIResponse(
                task=task, content="", model="unknown", error="No hay proveedores IA disponibles"
            )
            if db and request_id:
                AILogger.log_error(db, request_id, response.error)
            return response

        fallback_policy = _get_ai_fallback_policy(request)
        policy_enabled = (
            _policy_bool(fallback_policy, "enabled", True) if fallback_policy else False
        )

        if (
            provider is None
            and ai_provider.name == "ollama"
            and fallback_policy
            and policy_enabled
            and await _should_route_to_openai_before_call(
                request, current_provider_name=ai_provider.name
            )
        ):
            openai_provider = AIProviderFactory.get_provider("openai")
            if openai_provider and await openai_provider.health_check():
                logger.info(
                    "Routing %s request directly to OpenAI because complexity_score=%.3f >= %.3f",
                    task,
                    _policy_float(fallback_policy, "complexity_score", 0.0),
                    _policy_float(fallback_policy, "complexity_threshold", 0.72),
                )
                ai_provider = openai_provider

        # Ejecutar con fallback controlado por política y cadena de proveedores.
        tried: set[str] = set()
        response: AIResponse | None = None
        current_provider = ai_provider

        while current_provider is not None:
            tried.add(current_provider.name)
            try:
                response = await current_provider.call(request)
            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"Error en IA query ({current_provider.name}): {error_msg}", exc_info=True
                )
                if db and request_id:
                    AILogger.log_error(db, request_id, error_msg)
                response = AIResponse(
                    task=task,
                    content="",
                    model=current_provider.name,
                    error=error_msg[:500],
                )

            if not response.is_error:
                break

            # Si falla Ollama, solo se permite OpenAI cuando la política lo habilita.
            if current_provider.name == "ollama":
                if not fallback_policy or not policy_enabled:
                    break
                if not _policy_bool(fallback_policy, "allow_on_error", False):
                    break
                if await _openai_cooldown_active():
                    break

                next_provider = AIProviderFactory.get_provider("openai")
                if not next_provider or not await next_provider.health_check():
                    break
            else:
                fallback_chain = AIProviderFactory._fallback_chain
                next_provider = None
                for pname in fallback_chain:
                    if pname not in tried:
                        if pname == "openai" and await _openai_cooldown_active():
                            continue
                        candidate = AIProviderFactory.get_provider(pname)
                        if candidate and await candidate.health_check():
                            next_provider = candidate
                            break

            if next_provider is None:
                break

            logger.warning(
                "Proveedor %s devolvio error (%s), escalando a %s",
                current_provider.name,
                (response.error or "")[:100],
                next_provider.name,
            )
            current_provider = next_provider

        # Log respuesta final
        if db and request_id:
            from app.models.ai_log import AIResponseStatus

            status = AIResponseStatus.SUCCESS if not response.is_error else AIResponseStatus.ERROR
            AILogger.log_response(db, request_id, response, status=status)

        if response and not response.is_error:
            await _store_response_in_cache(tenant_id, request, response)

        logger.debug(
            f"IA query ({task}): {current_provider.name if current_provider else 'unknown'} - {response.processing_time_ms if response else 0}ms"
        )

        if response and not response.is_error:
            return response

        # Intentar recuperación como ultimo recurso
        if enable_recovery and db and request_id:
            recovered = await recovery_manager.recover(
                request,
                db,
                request_id,
                response.error if response and response.error else "no response",
            )
            if recovered and not recovered.is_error:
                return recovered

        if response is not None:
            return response

        return AIResponse(
            task=task,
            content="",
            model=current_provider.name if current_provider else "unknown",
            error="No se obtuvo respuesta de ningún proveedor",
        )

    @staticmethod
    async def classify_document(
        document_content: str,
        expected_types: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
        """
        Clasifica un documento en uno de los tipos esperados

        Args:
            document_content: Contenido o resumen del documento
            expected_types: Lista de tipos posibles
            confidence_threshold: Umbral mínimo de confianza

        Returns:
            {
                "type": str,
                "confidence": float,
                "explanation": str,
                "requires_review": bool
            }
        """
        prompt = f"""Clasifica este documento en una de estas categorías:
{chr(10).join(f'- {t}' for t in expected_types)}

Documento:
{document_content}

Responde SOLO con JSON válido con keys: type, confidence (0-1), explanation"""

        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=500,
        )

        if response.is_error:
            return {
                "type": "unknown",
                "confidence": 0.0,
                "explanation": response.error,
                "requires_review": True,
            }

        try:
            data = json.loads(response.content)
            confidence = data.get("confidence", 0.0)
            return {
                "type": data.get("type", "unknown"),
                "confidence": confidence,
                "explanation": data.get("explanation", ""),
                "requires_review": confidence < confidence_threshold,
            }
        except json.JSONDecodeError:
            logger.warning(f"No se pudo parsear respuesta de clasificación: {response.content}")
            return {
                "type": "unknown",
                "confidence": 0.0,
                "explanation": "Error parseando respuesta",
                "requires_review": True,
            }

    @staticmethod
    async def generate_suggestion(
        context: str,
        suggestion_type: str = "general",
    ) -> str:
        """
        Genera sugerencias contextuales inteligentes

        Args:
            context: Contexto para generar sugerencia
            suggestion_type: Tipo de sugerencia (general, improvement, alert, etc)

        Returns:
            Texto con sugerencia
        """
        prompt = f"""Contexto: {context}
Da UNA sugerencia breve y accionable (máximo 2 oraciones)."""

        response = await AIService.query(
            task=AITask.SUGGESTION,
            prompt=prompt,
            temperature=0.5,
            max_tokens=100,
        )

        return response.content if not response.is_error else ""

    @staticmethod
    async def analyze_incident(
        incident_type: str,
        description: str,
        stack_trace: str | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Analiza incidencia y proporciona sugerencias

        Args:
            incident_type: Tipo de incidencia
            description: Descripción del problema
            stack_trace: Stack trace si aplica
            additional_context: Contexto adicional

        Returns:
            {
                "root_cause": str,
                "impact": str,
                "recommended_actions": [str],
                "priority": "low|medium|high|critical"
            }
        """
        prompt = f"""Analiza esta incidencia y proporciona diagnóstico:

TIPO: {incident_type}
DESCRIPCIÓN: {description}
"""

        if stack_trace:
            prompt += f"STACK TRACE:\n{stack_trace}\n"

        if additional_context:
            prompt += f"CONTEXTO:\n{json.dumps(additional_context, indent=2)}\n"

        prompt += """
Responde SOLO con JSON con keys:
- root_cause: str
- impact: str
- recommended_actions: [str]
- priority: "low"|"medium"|"high"|"critical"
"""

        response = await AIService.query(
            task=AITask.ANALYSIS,
            prompt=prompt,
            temperature=0.3,
            max_tokens=1000,
        )

        if response.is_error:
            return {
                "root_cause": "Error analizando",
                "impact": response.error,
                "recommended_actions": ["Revisar manualmente"],
                "priority": "medium",
            }

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            logger.warning(f"No se pudo parsear análisis: {response.content}")
            return {
                "root_cause": "Error parseando análisis",
                "impact": "Unknown",
                "recommended_actions": ["Revisar manualmente"],
                "priority": "medium",
            }

    @staticmethod
    async def generate_document_draft(
        document_type: str,
        data: dict[str, Any],
        template: str | None = None,
    ) -> dict[str, Any]:
        """
        Genera borrador de documento (factura, orden, etc)

        Args:
            document_type: Tipo de documento (invoice, order, transfer, etc)
            data: Datos para generar documento
            template: Template custom si aplica

        Returns:
            {
                "content": str,
                "fields": dict,
                "warnings": [str]
            }
        """
        prompt = f"""Genera un {document_type} en formato JSON basado en estos datos:

{json.dumps(data, indent=2, ensure_ascii=False)}

Valida que todos los datos sean consistentes y coherentes.
Retorna SOLO JSON con keys: content, fields (dict), warnings (list)"""

        response = await AIService.query(
            task=AITask.GENERATION,
            prompt=prompt,
            temperature=0.2,
            max_tokens=1500,
        )

        if response.is_error:
            return {
                "content": "",
                "fields": {},
                "warnings": [response.error],
            }

        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "content": response.content,
                "fields": {},
                "warnings": ["Respuesta no fue JSON válido"],
            }
