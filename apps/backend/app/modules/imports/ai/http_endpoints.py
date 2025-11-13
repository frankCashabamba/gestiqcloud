"""HTTP endpoints for AI classification and telemetry."""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from .telemetry import telemetry
from app.modules.imports.ai import get_ai_provider_singleton
from app.config.settings import settings

logger = logging.getLogger("imports.ai.http")

router = APIRouter(prefix="/imports/ai", tags=["imports-ai"])


class ClassifyDocumentRequest(BaseModel):
    """Request to classify a document."""
    text: str
    available_parsers: list[str]
    use_ai_enhancement: bool = True


class ClassifyDocumentResponse(BaseModel):
    """Response from classification."""
    suggested_parser: str
    confidence: float
    probabilities: Dict[str, float]
    reasoning: str
    provider: str
    enhanced_by_ai: bool


class AIStatusResponse(BaseModel):
    """AI provider status."""
    provider: str
    status: str
    telemetry: Dict[str, Any]
    threshold: float
    cache_enabled: bool


@router.post("/classify", response_model=ClassifyDocumentResponse)
async def classify_document(
    request: ClassifyDocumentRequest,
    tenant_id: Optional[str] = Query(None),
):
    """
    Classify a document to select the best parser.
    
    Endpoint: POST /imports/ai/classify
    
    Args:
        text: Document text content
        available_parsers: List of available parser IDs
        use_ai_enhancement: Whether to use AI enhancement if confidence is low
        tenant_id: Optional tenant ID for tracking
    
    Returns:
        Classification result with suggested parser and confidence
    """
    try:
        provider = await get_ai_provider_singleton()
        
        # Classify
        result = await provider.classify_document(
            text=request.text,
            available_parsers=request.available_parsers,
            doc_metadata={"tenant_id": tenant_id} if tenant_id else None,
        )
        
        logger.info(
            f"Classification: {result.suggested_parser} "
            f"(confidence: {result.confidence:.0%}, "
            f"provider: {result.provider})"
        )
        
        return ClassifyDocumentResponse(**result.__dict__)
    
    except Exception as e:
        logger.error(f"Classification error: {e}")
        raise


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status(
    tenant_id: Optional[str] = Query(None),
):
    """
    Get AI provider status and telemetry.
    
    Endpoint: GET /imports/ai/status
    
    Returns:
        Current AI provider status and usage metrics
    """
    try:
        provider = await get_ai_provider_singleton()
        
        return AIStatusResponse(
            provider=settings.IMPORT_AI_PROVIDER,
            status="active",
            telemetry=provider.get_telemetry(),
            threshold=settings.IMPORT_AI_CONFIDENCE_THRESHOLD,
            cache_enabled=settings.IMPORT_AI_CACHE_ENABLED,
        )
    
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise


class TelemetryResponse(BaseModel):
    """Telemetry summary response."""
    total_requests: int
    providers: Dict[str, Any]
    total_cost: float
    avg_confidence: float
    avg_time_ms: float


@router.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry(
    provider: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
):
    """
    Get AI classification telemetry and accuracy metrics.
    
    Endpoint: GET /imports/ai/telemetry
    
    Args:
        provider: Filter by provider (local, openai, azure)
        tenant_id: Optional tenant ID
    
    Returns:
        Telemetry summary with accuracy and cost metrics
    """
    try:
        summary = telemetry.get_summary()
        
        if not summary:
            return TelemetryResponse(
                total_requests=0,
                providers={},
                total_cost=0.0,
                avg_confidence=0.0,
                avg_time_ms=0.0,
            )
        
        return TelemetryResponse(**summary)
    
    except Exception as e:
        logger.error(f"Telemetry retrieval error: {e}")
        raise


class MetricsExportResponse(BaseModel):
    """Metrics export response."""
    metrics: list[Dict[str, Any]]
    count: int
    provider_filter: Optional[str]


@router.get("/metrics/export", response_model=MetricsExportResponse)
async def export_metrics(
    provider: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
):
    """
    Export detailed metrics for analysis.
    
    Endpoint: GET /imports/ai/metrics/export
    
    Args:
        provider: Filter by provider
        tenant_id: Optional tenant ID
    
    Returns:
        List of detailed metric records
    """
    try:
        metrics = telemetry.export_metrics(provider=provider)
        
        return MetricsExportResponse(
            metrics=metrics,
            count=len(metrics),
            provider_filter=provider,
        )
    
    except Exception as e:
        logger.error(f"Metrics export error: {e}")
        raise


class ValidateMetricRequest(BaseModel):
    """Request to validate a classification result."""
    metric_index: int
    correct: bool
    feedback: Optional[str] = None


@router.post("/metrics/validate")
async def validate_metric(
    request: ValidateMetricRequest,
    tenant_id: Optional[str] = Query(None),
):
    """
    Mark a classification as correct or incorrect for accuracy tracking.
    
    Endpoint: POST /imports/ai/metrics/validate
    
    Args:
        metric_index: Index of metric to validate
        correct: Whether the classification was correct
        feedback: Optional feedback comment
    
    Returns:
        Confirmation message
    """
    try:
        telemetry.mark_correct(request.metric_index, request.correct)
        
        logger.info(
            f"Metric validated: index={request.metric_index}, "
            f"correct={request.correct}"
        )
        
        return {
            "status": "ok",
            "message": "Metric validated",
            "accuracy": telemetry.get_accuracy(),
        }
    
    except Exception as e:
        logger.error(f"Metric validation error: {e}")
        raise


# Health check
@router.get("/health")
async def health_check():
    """Quick health check for AI provider."""
    try:
        provider = await get_ai_provider_singleton()
        return {
            "status": "healthy",
            "provider": settings.IMPORT_AI_PROVIDER,
            "telemetry": provider.get_telemetry(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "provider": settings.IMPORT_AI_PROVIDER,
            "error": str(e),
        }
