"""
Servicio Unificado de IA - API consistente para todas las características
Con logging automático, análisis de errores y recuperación
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.ai.base import AIRequest, AIResponse, AIResponse, AITask
from app.services.ai.factory import AIProviderFactory
from app.services.ai.logging import AILogger, AIMetrics
from app.services.ai.recovery import recovery_manager

logger = logging.getLogger(__name__)


class AIService:
    """Servicio unificado de IA con fallback automático y recuperación de errores"""
    
    @staticmethod
    async def query(
        task: AITask,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        provider: Optional[str] = None,
        db: Optional[Session] = None,
        tenant_id: Optional[str] = None,
        module: Optional[str] = None,
        user_id: Optional[str] = None,
        enable_recovery: bool = True,
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
        )
        
        # Generar ID para tracking
        request_id = None
        if db:
            try:
                ai_provider = await AIProviderFactory.get_available_provider(task)
                provider_model = ai_provider.default_model if ai_provider else "unknown"
                request_id = AILogger.log_request(
                    db,
                    request,
                    provider_name=provider or "auto",
                    provider_model=str(provider_model),
                    tenant_id=tenant_id,
                    module=module,
                    user_id=user_id,
                )
            except Exception as e:
                logger.debug(f"Error logging request: {e}")
        
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
                task=task,
                content="",
                model="unknown",
                error="No hay proveedores IA disponibles"
            )
            if db and request_id:
                AILogger.log_error(db, request_id, response.error)
            return response
        
        # Ejecutar
        try:
            response = await ai_provider.call(request)
            
            # Log respuesta exitosa
            if db and request_id:
                from app.models.ai_log import AIResponseStatus
                status = AIResponseStatus.SUCCESS if not response.is_error else AIResponseStatus.ERROR
                AILogger.log_response(db, request_id, response, status=status)
            
            logger.debug(f"IA query ({task}): {ai_provider.name} - {response.processing_time_ms}ms")
            return response
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error en IA query: {error_msg}", exc_info=True)
            
            # Log error
            if db and request_id:
                AILogger.log_error(db, request_id, error_msg)
            
            # Intentar recuperación
            if enable_recovery and db and request_id:
                recovered_response = await recovery_manager.recover(
                    request, db, request_id, error_msg
                )
                if recovered_response and not recovered_response.is_error:
                    return recovered_response
            
            # Fallback response
            return AIResponse(
                task=task,
                content="",
                model=ai_provider.name if ai_provider else "unknown",
                error=error_msg[:500],
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
        prompt = f"""Basándote en este contexto empresarial, genera una sugerencia útil y accionable:

Contexto: {context}
Tipo: {suggestion_type}

Sé conciso y específico."""
        
        response = await AIService.query(
            task=AITask.SUGGESTION,
            prompt=prompt,
            temperature=0.5,
            max_tokens=300,
        )
        
        return response.content if not response.is_error else ""
    
    @staticmethod
    async def analyze_incident(
        incident_type: str,
        description: str,
        stack_trace: Optional[str] = None,
        additional_context: Optional[dict[str, Any]] = None,
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
        template: Optional[str] = None,
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
