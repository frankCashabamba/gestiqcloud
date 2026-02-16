"""
Sistema de logging y análisis de requests/responses de IA
Permite auditoría, análisis de errores y mejora continua
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.ai_log import AIRequestLog, AIResponseStatus, AITaskLog, AIErrorAnalysis, AIErrorRecovery
from app.services.ai.base import AIRequest, AIResponse, AITask

logger = logging.getLogger(__name__)


class AILogger:
    """Logger centralizado para requests/responses de IA"""

    @staticmethod
    def log_request(
        db: Session,
        request: AIRequest,
        provider_name: str,
        provider_model: str,
        tenant_id: Optional[str] = None,
        module: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Registra un request de IA
        
        Returns:
            request_id para tracking
        """
        try:
            request_id = str(uuid.uuid4())
            
            # Calcular hash del prompt para dedup
            prompt_hash = hashlib.sha256(request.prompt.encode()).hexdigest()
            
            log_entry = AIRequestLog(
                request_id=request_id,
                tenant_id=tenant_id,
                module=module,
                user_id=user_id,
                task=request.task.value,
                prompt_length=len(request.prompt),
                prompt_hash=prompt_hash,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                model_requested=str(request.model) if request.model else None,
                provider_used=provider_name,
                provider_model=provider_model,
                status=AIResponseStatus.SUCCESS.value,  # Por defecto
                request_metadata=metadata or {},
            )
            
            db.add(log_entry)
            db.commit()
            
            logger.debug(f"Request logging: {request_id} ({module}/{request.task.value})")
            return request_id
            
        except Exception as e:
            logger.error(f"Error logging request: {e}")
            return str(uuid.uuid4())  # Retornar ID anyway

    @staticmethod
    def log_response(
        db: Session,
        request_id: str,
        response: AIResponse,
        status: AIResponseStatus = AIResponseStatus.SUCCESS,
        retry_count: int = 0,
        fallback_used: Optional[str] = None,
    ) -> None:
        """
        Registra response y resultado
        """
        try:
            log_entry = db.query(AIRequestLog).filter(
                AIRequestLog.request_id == request_id
            ).first()
            
            if not log_entry:
                logger.warning(f"Request log not found: {request_id}")
                return
            
            # Actualizar con respuesta
            log_entry.status = status.value
            log_entry.response_content_length = len(response.content)
            log_entry.tokens_used = response.tokens_used
            log_entry.processing_time_ms = response.processing_time_ms
            log_entry.retry_count = retry_count
            log_entry.fallback_used = fallback_used
            log_entry.confidence_score = response.confidence
            
            if response.is_error:
                log_entry.error_message = response.error
                log_entry.error_code = response.error[:50] if response.error else None
            
            log_entry.response_metadata = response.metadata or {}
            log_entry.updated_at = datetime.utcnow()
            
            db.commit()
            logger.debug(f"Response logged: {request_id} (status={status.value})")
            
        except Exception as e:
            logger.error(f"Error logging response: {e}")

    @staticmethod
    def log_error(
        db: Session,
        request_id: str,
        error_message: str,
        error_code: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> None:
        """
        Registra error específico
        """
        try:
            log_entry = db.query(AIRequestLog).filter(
                AIRequestLog.request_id == request_id
            ).first()
            
            if log_entry:
                log_entry.status = AIResponseStatus.ERROR.value
                log_entry.error_message = error_message[:500]
                log_entry.error_code = error_code or "unknown"
                log_entry.updated_at = datetime.utcnow()
                db.commit()
            
            # Analizar patrón de error
            AILogger._analyze_error_pattern(db, error_message, provider_name)
            
        except Exception as e:
            logger.error(f"Error logging error: {e}")

    @staticmethod
    def _analyze_error_pattern(
        db: Session,
        error_message: str,
        provider_name: Optional[str] = None,
    ) -> None:
        """
        Analiza patrones de error y actualiza análisis
        """
        try:
            # Simplificar mensaje para pattern matching
            pattern = error_message[:50].lower()
            if provider_name:
                pattern = f"{provider_name}_{pattern}"
            
            error_analysis = db.query(AIErrorAnalysis).filter(
                AIErrorAnalysis.error_message_pattern.like(f"%{pattern[:30]}%")
            ).first()
            
            if error_analysis:
                error_analysis.occurrence_count += 1
                error_analysis.last_occurred = datetime.utcnow()
            else:
                # Crear nuevo análisis
                error_analysis = AIErrorAnalysis(
                    error_pattern=pattern[:100],
                    error_code=error_message.split(":")[0][:50],
                    error_message_pattern=error_message[:255],
                    probable_cause="Error recurrente detectado",
                    suggested_action="Revisar logs y configuración"
                )
                db.add(error_analysis)
            
            db.commit()
            logger.info(f"Error pattern tracked: {pattern}")
            
        except Exception as e:
            logger.debug(f"Could not analyze error pattern: {e}")

    @staticmethod
    def log_recovery_attempt(
        db: Session,
        request_id: str,
        strategy_name: str,
        action_taken: str,
        success: bool,
        recovery_time_ms: int,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Registra intento de recuperación de error
        """
        try:
            recovery = AIErrorRecovery(
                request_log_id=None,  # Se actualiza si encontramos el log
                strategy_name=strategy_name,
                step_number=1,
                action_taken=action_taken,
                was_successful="true" if success else "false",
                recovery_time_ms=recovery_time_ms,
                recovery_result=result or {},
            )
            
            db.add(recovery)
            db.commit()
            
            logger.info(f"Recovery logged: {strategy_name} ({'success' if success else 'failed'})")
            
        except Exception as e:
            logger.error(f"Error logging recovery: {e}")


class AIMetrics:
    """Métricas y estadísticas de IA"""

    @staticmethod
    def get_error_rate(
        db: Session,
        hours: int = 24,
        module: Optional[str] = None,
    ) -> float:
        """
        Calcula tasa de error en últimas N horas
        
        Returns:
            Porcentaje (0-100)
        """
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(AIRequestLog).filter(
                AIRequestLog.created_at >= cutoff
            )
            
            if module:
                query = query.filter(AIRequestLog.module == module)
            
            total = query.count()
            errors = query.filter(
                AIRequestLog.status.in_([
                    AIResponseStatus.ERROR.value,
                    AIResponseStatus.TIMEOUT.value,
                    AIResponseStatus.INVALID.value,
                ])
            ).count()
            
            if total == 0:
                return 0.0
            
            return (errors / total) * 100
            
        except Exception as e:
            logger.error(f"Error calculating error rate: {e}")
            return 0.0

    @staticmethod
    def get_provider_performance(
        db: Session,
        hours: int = 24,
    ) -> dict[str, Any]:
        """
        Performance de cada proveedor
        """
        try:
            from datetime import timedelta
            from sqlalchemy import avg, func
            
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            results = db.query(
                AIRequestLog.provider_used,
                func.count(AIRequestLog.id).label("total"),
                func.sum(
                    (AIRequestLog.status == AIResponseStatus.SUCCESS.value).cast(Integer)
                ).label("success"),
                func.avg(AIRequestLog.processing_time_ms).label("avg_time_ms"),
                func.avg(AIRequestLog.tokens_used).label("avg_tokens"),
            ).filter(
                AIRequestLog.created_at >= cutoff
            ).group_by(
                AIRequestLog.provider_used
            ).all()
            
            performance = {}
            for provider, total, success, avg_time, avg_tokens in results:
                success_rate = (success / total * 100) if total > 0 else 0
                performance[provider] = {
                    "total_requests": total,
                    "success_count": success or 0,
                    "success_rate": float(success_rate),
                    "avg_time_ms": float(avg_time) if avg_time else 0,
                    "avg_tokens": float(avg_tokens) if avg_tokens else 0,
                }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error getting provider performance: {e}")
            return {}

    @staticmethod
    def get_top_errors(
        db: Session,
        limit: int = 10,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Top errores en últimas N horas
        """
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            errors = db.query(
                AIRequestLog.error_code,
                AIRequestLog.error_message,
                func.count(AIRequestLog.id).label("count"),
            ).filter(
                AIRequestLog.created_at >= cutoff,
                AIRequestLog.status == AIResponseStatus.ERROR.value,
            ).group_by(
                AIRequestLog.error_code,
                AIRequestLog.error_message,
            ).order_by(
                func.count(AIRequestLog.id).desc()
            ).limit(limit).all()
            
            return [
                {
                    "error_code": code,
                    "error_message": msg,
                    "count": count,
                }
                for code, msg, count in errors
            ]
            
        except Exception as e:
            logger.error(f"Error getting top errors: {e}")
            return []

    @staticmethod
    def get_slowest_requests(
        db: Session,
        limit: int = 10,
        hours: int = 24,
    ) -> list[dict[str, Any]]:
        """
        Requests más lentos
        """
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            
            slow = db.query(AIRequestLog).filter(
                AIRequestLog.created_at >= cutoff,
                AIRequestLog.processing_time_ms.isnot(None),
            ).order_by(
                AIRequestLog.processing_time_ms.desc()
            ).limit(limit).all()
            
            return [
                {
                    "request_id": log.request_id,
                    "task": log.task,
                    "provider": log.provider_used,
                    "time_ms": log.processing_time_ms,
                    "status": log.status,
                }
                for log in slow
            ]
            
        except Exception as e:
            logger.error(f"Error getting slowest requests: {e}")
            return []
