"""
Endpoints para logs, métricas y análisis de IA
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.ai_log import AIRequestLog, AIErrorAnalysis, AIResponseStatus
from app.services.ai.logging import AILogger, AIMetrics
from app.services.ai.recovery import recovery_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai/logs", tags=["AI Logs & Metrics"])


# ============================================================================
# SCHEMAS
# ============================================================================


class AIRequestLogOut(BaseModel):
    """Respuesta de request log"""

    request_id: str
    task: str
    status: str
    provider_used: str
    processing_time_ms: Optional[int]
    tokens_used: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    module: Optional[str]

    class Config:
        from_attributes = True


class ErrorStatisticsOut(BaseModel):
    """Estadísticas de errores"""

    total_requests: int
    error_count: int
    error_rate: float
    timeout_count: int
    success_count: int
    avg_processing_time_ms: float


class ProviderPerformanceOut(BaseModel):
    """Performance de proveedor"""

    provider: str
    total_requests: int
    success_rate: float
    avg_time_ms: float
    avg_tokens: float


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/recent", response_model=list[AIRequestLogOut])
async def get_recent_logs(
    limit: int = Query(20, ge=1, le=100),
    module: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Obtiene logs recientes
    
    Args:
        limit: Número de registros (máx 100)
        module: Filtrar por módulo (copilot, imports, etc)
        status: Filtrar por estado (success, error, timeout)
    """
    try:
        query = db.query(AIRequestLog).order_by(AIRequestLog.created_at.desc())

        if module:
            query = query.filter(AIRequestLog.module == module)

        if status:
            query = query.filter(AIRequestLog.status == status)

        logs = query.limit(limit).all()
        return logs

    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        raise HTTPException(status_code=500, detail="Error fetching logs")


@router.get("/statistics", response_model=ErrorStatisticsOut)
async def get_error_statistics(
    hours: int = Query(24, ge=1, le=168),
    module: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Obtiene estadísticas de errores
    
    Args:
        hours: Período a analizar (1-168 horas)
        module: Filtrar por módulo
    """
    try:
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        query = db.query(AIRequestLog).filter(AIRequestLog.created_at >= cutoff)

        if module:
            query = query.filter(AIRequestLog.module == module)

        total = query.count()
        errors = query.filter(
            AIRequestLog.status.in_(
                [
                    AIResponseStatus.ERROR.value,
                    AIResponseStatus.INVALID.value,
                ]
            )
        ).count()
        timeouts = query.filter(AIRequestLog.status == AIResponseStatus.TIMEOUT.value).count()
        success = query.filter(AIRequestLog.status == AIResponseStatus.SUCCESS.value).count()

        from sqlalchemy import func

        avg_time = db.query(func.avg(AIRequestLog.processing_time_ms)).filter(
            AIRequestLog.created_at >= cutoff
        ).scalar() or 0

        error_rate = (errors / total * 100) if total > 0 else 0

        return ErrorStatisticsOut(
            total_requests=total,
            error_count=errors,
            error_rate=error_rate,
            timeout_count=timeouts,
            success_count=success,
            avg_processing_time_ms=float(avg_time),
        )

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Error getting statistics")


@router.get("/providers", response_model=dict[str, Any])
async def get_provider_performance(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Obtiene performance de cada proveedor
    
    Args:
        hours: Período a analizar
    """
    try:
        performance = AIMetrics.get_provider_performance(db, hours=hours)

        return {
            "period_hours": hours,
            "providers": performance,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting provider performance: {e}")
        raise HTTPException(status_code=500, detail="Error getting performance data")


@router.get("/errors/top", response_model=list[dict[str, Any]])
async def get_top_errors(
    limit: int = Query(10, ge=1, le=50),
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Obtiene top errores recientes
    
    Args:
        limit: Número de errores (máx 50)
        hours: Período a analizar
    """
    try:
        errors = AIMetrics.get_top_errors(db, limit=limit, hours=hours)
        return errors

    except Exception as e:
        logger.error(f"Error getting top errors: {e}")
        raise HTTPException(status_code=500, detail="Error getting errors")


@router.get("/requests/slow", response_model=list[dict[str, Any]])
async def get_slowest_requests(
    limit: int = Query(10, ge=1, le=50),
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Obtiene requests más lentos
    
    Args:
        limit: Número de requests (máx 50)
        hours: Período a analizar
    """
    try:
        slow = AIMetrics.get_slowest_requests(db, limit=limit, hours=hours)
        return slow

    except Exception as e:
        logger.error(f"Error getting slowest requests: {e}")
        raise HTTPException(status_code=500, detail="Error getting slowest requests")


@router.get("/{request_id}", response_model=AIRequestLogOut)
async def get_request_log(
    request_id: str,
    db: Session = Depends(get_db),
):
    """
    Obtiene log específico de un request
    
    Args:
        request_id: ID del request
    """
    try:
        log = db.query(AIRequestLog).filter(AIRequestLog.request_id == request_id).first()

        if not log:
            raise HTTPException(status_code=404, detail="Request not found")

        return log

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting request log: {e}")
        raise HTTPException(status_code=500, detail="Error fetching log")


@router.get("/analysis/summary", response_model=dict[str, Any])
async def get_analysis_summary(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """
    Resumen de análisis de errores
    
    Returns:
        Análisis y recomendaciones
    """
    try:
        # Obtener errores frecuentes
        top_errors = AIMetrics.get_top_errors(db, limit=5, hours=hours)

        # Obtener performance
        performance = AIMetrics.get_provider_performance(db, hours=hours)

        # Tasa de error
        error_rate = AIMetrics.get_error_rate(db, hours=hours)

        # Recomendaciones
        recommendations = []

        if error_rate > 10:
            recommendations.append("❌ Tasa de error alto (>10%). Revisar logs de error.")

        slow_requests = AIMetrics.get_slowest_requests(db, limit=1, hours=hours)
        if slow_requests and slow_requests[0]["time_ms"] > 30000:
            recommendations.append("⚠️ Requests lentos (>30s). Considerar timeout o fallback.")

        # Provider con mejor performance
        best_provider = max(
            performance.items(),
            key=lambda x: x[1].get("success_rate", 0),
            default=(None, {}),
        )

        if best_provider[0]:
            recommendations.append(f"✅ Mejor proveedor: {best_provider[0]} ({best_provider[1].get('success_rate', 0):.1f}% éxito)")

        return {
            "period_hours": hours,
            "error_rate": f"{error_rate:.2f}%",
            "total_errors": len(top_errors),
            "top_errors": top_errors,
            "provider_performance": performance,
            "recommendations": recommendations or ["✅ Sistema funcionando normalmente"],
            "analyzed_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting analysis summary: {e}")
        raise HTTPException(status_code=500, detail="Error getting analysis")


@router.post("/errors/{error_code}/fix", response_model=dict[str, Any])
async def suggest_error_fix(
    error_code: str,
    error_message: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Obtiene sugerencias para fixear un error
    
    Args:
        error_code: Código del error
        error_message: Mensaje del error
    """
    try:
        fix_suggestions = await recovery_manager.suggest_fix(db, error_code, error_message)
        return fix_suggestions

    except Exception as e:
        logger.error(f"Error suggesting fix: {e}")
        raise HTTPException(status_code=500, detail="Error generating fix suggestions")


@router.delete("/old-logs")
async def cleanup_old_logs(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """
    Elimina logs antiguos
    
    Args:
        days: Eliminar logs más antiguos que N días
    """
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)

        deleted = (
            db.query(AIRequestLog).filter(AIRequestLog.created_at < cutoff).delete()
        )

        db.commit()

        return {
            "deleted_records": deleted,
            "cutoff_date": cutoff.isoformat(),
            "message": f"Eliminados {deleted} logs anteriores a {days} días",
        }

    except Exception as e:
        logger.error(f"Error cleaning logs: {e}")
        raise HTTPException(status_code=500, detail="Error cleaning logs")
