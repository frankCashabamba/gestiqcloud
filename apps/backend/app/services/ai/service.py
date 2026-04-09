"""
Servicio unificado de IA.
Prioriza una ruta simple: cache -> proveedor primario -> fallback solo por error real.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

from sqlalchemy.orm import Session

from app.core.cache import CacheTTL, build_cache_key, cache_get, cache_set
from app.services.ai.base import AIRequest, AIResponse, AITask, model_name
from app.services.ai.factory import AIProviderFactory
from app.services.ai.logging import AILogger
from app.services.ai.recovery import recovery_manager

logger = logging.getLogger(__name__)

_OPENAI_COOLDOWN_KEY = build_cache_key("global", "ai", "openai_rate_limit")
_OPENAI_COOLDOWN_SECONDS = max(60, int(os.getenv("OPENAI_COOLDOWN_SECONDS", "300")))


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


def _next_fallback_provider(current_name: str):
    for provider_name in AIProviderFactory._fallback_chain:
        if provider_name == current_name:
            continue
        candidate = AIProviderFactory.get_provider(provider_name)
        if candidate is not None and candidate.name != current_name:
            return candidate
    return None


class AIService:
    """Servicio unificado de IA."""

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
        bypass_cache: bool = False,
    ) -> AIResponse:
        request = AIRequest(
            task=task,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            context=context,
            model=model or None,
            messages=messages,
        )

        if bypass_cache:
            logger.info("AI cache bypassed task=%s tenant=%s", task.value, tenant_id or "global")
        else:
            cached_response = await _load_response_from_cache(tenant_id, request)
            if cached_response:
                logger.info("AI cache hit task=%s tenant=%s", task.value, tenant_id or "global")
                if db:
                    try:
                        request_id = AILogger.log_request(
                            db,
                            request,
                            provider_name="cache",
                            provider_model=str(cached_response.model),
                            tenant_id=tenant_id,
                            module=module,
                            user_id=user_id,
                        )
                        AILogger.log_response(db, request_id, cached_response)
                    except Exception as exc:
                        logger.debug("Error logging cached AI response: %s", exc)
                return cached_response

        requested_provider = provider.strip().lower() if provider else None
        ai_provider = (
            AIProviderFactory.get_provider(requested_provider)
            if requested_provider
            else AIProviderFactory.get_provider()
        )
        if not ai_provider:
            response = AIResponse(
                task=task,
                content="",
                model="unknown",
                error="No hay proveedores IA disponibles",
            )
            if db:
                try:
                    request_id = AILogger.log_request(
                        db,
                        request,
                        provider_name=requested_provider or "auto",
                        provider_model="unknown",
                        tenant_id=tenant_id,
                        module=module,
                        user_id=user_id,
                    )
                    AILogger.log_response(db, request_id, response)
                except Exception:
                    logger.debug("Error logging unavailable-provider response", exc_info=True)
            return response

        requested_model = model_name(model) or None

        fallback_provider = None
        if requested_provider is None:
            fallback_provider = _next_fallback_provider(ai_provider.name)

        logger.info(
            "AI provider selected task=%s provider=%s requested_model=%s fallback=%s",
            task.value,
            ai_provider.name,
            requested_model or ai_provider.default_model,
            fallback_provider.name if fallback_provider else "none",
        )

        request_id = None
        if db:
            try:
                request_id = AILogger.log_request(
                    db,
                    request,
                    provider_name=ai_provider.name,
                    provider_model=str(requested_model or ai_provider.default_model),
                    tenant_id=tenant_id,
                    module=module,
                    user_id=user_id,
                )
            except Exception as exc:
                logger.debug("Error logging request: %s", exc)

        async def _invoke(provider_obj):
            started_at = time.perf_counter()
            response_obj = await provider_obj.call(request)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            if response_obj.processing_time_ms <= 0:
                response_obj.processing_time_ms = elapsed_ms
            logger.info(
                "AI provider finished task=%s provider=%s resolved_model=%s status=%s elapsed_ms=%s",
                task.value,
                provider_obj.name,
                response_obj.model,
                "error" if response_obj.is_error or not response_obj.content.strip() else "ok",
                response_obj.processing_time_ms,
            )
            return response_obj

        response = await _invoke(ai_provider)
        final_provider_name = ai_provider.name

        if response.is_error or not response.content.strip():
            if not response.is_error and not response.content.strip():
                response = AIResponse(
                    task=task,
                    content="",
                    model=response.model or ai_provider.name,
                    error="Respuesta vacía del proveedor",
                    processing_time_ms=response.processing_time_ms,
                    metadata=response.metadata,
                )

            if (
                requested_provider is None
                and fallback_provider is not None
                and fallback_provider.name != ai_provider.name
            ):
                if fallback_provider.name == "openai" and await _openai_cooldown_active():
                    logger.info(
                        "OpenAI fallback skipped task=%s provider=%s cooldown=active",
                        task.value,
                        ai_provider.name,
                    )
                else:
                    logger.warning(
                        "AI fallback task=%s from=%s to=%s reason=%s",
                        task.value,
                        ai_provider.name,
                        fallback_provider.name,
                        (response.error or "unknown")[:200],
                    )
                    fallback_response = await _invoke(fallback_provider)
                    final_provider_name = fallback_provider.name
                    if fallback_response.is_error or not fallback_response.content.strip():
                        if not fallback_response.is_error and not fallback_response.content.strip():
                            fallback_response = AIResponse(
                                task=task,
                                content="",
                                model=fallback_response.model or fallback_provider.name,
                                error="Respuesta vacía del proveedor",
                                processing_time_ms=fallback_response.processing_time_ms,
                                metadata=fallback_response.metadata,
                            )
                        response = fallback_response
                        if (
                            fallback_provider.name == "openai"
                            and response.error
                            and ("429" in response.error or "rate limit" in response.error.lower())
                        ):
                            await _register_openai_cooldown(reason=response.error)
                    else:
                        response = fallback_response

        if db and request_id:
            from app.models.ai_log import AIResponseStatus

            status = AIResponseStatus.SUCCESS if not response.is_error else AIResponseStatus.ERROR
            AILogger.log_response(
                db,
                request_id,
                response,
                status=status,
                fallback_used=(
                    final_provider_name if final_provider_name != ai_provider.name else None
                ),
                resolved_provider_model=response.model,
            )

        if not response.is_error and response.content.strip():
            if not bypass_cache:
                await _store_response_in_cache(tenant_id, request, response)

        logger.info(
            "AI query done task=%s provider=%s resolved_model=%s status=%s elapsed_ms=%s",
            task.value,
            final_provider_name,
            response.model,
            "error" if response.is_error else "ok",
            response.processing_time_ms,
        )

        if not response.is_error:
            return response

        if enable_recovery and db and request_id:
            recovered = await recovery_manager.recover(
                request,
                db,
                request_id,
                response.error if response.error else "no response",
            )
            if recovered and not recovered.is_error:
                return recovered

        return response

    @staticmethod
    async def classify_document(
        document_content: str,
        expected_types: list[str],
        confidence_threshold: float = 0.7,
    ) -> dict[str, Any]:
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
            logger.warning("No se pudo parsear respuesta de clasificación: %s", response.content)
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
            logger.warning("No se pudo parsear análisis: %s", response.content)
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
