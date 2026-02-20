"""HTTP endpoints for AI classification and telemetry."""

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.modules.imports.ai import get_ai_provider_singleton
from app.modules.imports.domain.mapping_feedback import MappingFeedback, mapping_learner

from .mapping_suggester import mapping_suggester
from .telemetry import telemetry

logger = logging.getLogger("imports.ai.http")

router = APIRouter(prefix="/ai", tags=["imports-ai"])


class ClassifyDocumentRequest(BaseModel):
    """Request to classify a document."""

    text: str
    available_parsers: list[str]
    use_ai_enhancement: bool = True


class ClassifyDocumentResponse(BaseModel):
    """Response from classification."""

    suggested_parser: str
    confidence: float
    probabilities: dict[str, float]
    reasoning: str
    provider: str
    enhanced_by_ai: bool


class AIStatusResponse(BaseModel):
    """AI provider status."""

    provider: str
    status: str
    telemetry: dict[str, Any]
    threshold: float
    cache_enabled: bool


@router.post("/classify", response_model=ClassifyDocumentResponse)
async def classify_document(
    request: ClassifyDocumentRequest,
    tenant_id: str | None = Query(None),
    provider: str | None = Query(None),
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
        ai_provider = await get_ai_provider_singleton(provider)

        # Classify
        result = await ai_provider.classify_document(
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
    tenant_id: str | None = Query(None),
    provider: str | None = Query(None),
):
    """
    Get AI provider status and telemetry.

    Endpoint: GET /imports/ai/status

    Returns:
        Current AI provider status and usage metrics
    """
    try:
        ai_provider = await get_ai_provider_singleton(provider)

        return AIStatusResponse(
            provider=provider or settings.IMPORT_AI_PROVIDER,
            status="active",
            telemetry=ai_provider.get_telemetry(),
            threshold=settings.IMPORT_AI_CONFIDENCE_THRESHOLD,
            cache_enabled=settings.IMPORT_AI_CACHE_ENABLED,
        )

    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise


class TelemetryResponse(BaseModel):
    """Telemetry summary response."""

    total_requests: int
    providers: dict[str, Any]
    total_cost: float
    avg_confidence: float
    avg_time_ms: float


@router.get("/telemetry", response_model=TelemetryResponse)
async def get_telemetry(
    provider: str | None = Query(None),
    tenant_id: str | None = Query(None),
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

    metrics: list[dict[str, Any]]
    count: int
    provider_filter: str | None


@router.get("/metrics/export", response_model=MetricsExportResponse)
async def export_metrics(
    provider: str | None = Query(None),
    tenant_id: str | None = Query(None),
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
    feedback: str | None = None


@router.post("/metrics/validate")
async def validate_metric(
    request: ValidateMetricRequest,
    tenant_id: str | None = Query(None),
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

        logger.info(f"Metric validated: index={request.metric_index}, correct={request.correct}")

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
async def health_check(provider: str | None = Query(None)):
    """Quick health check for AI provider."""
    try:
        ai_provider = await get_ai_provider_singleton(provider)
        current_provider = provider or settings.IMPORT_AI_PROVIDER
        available_providers = [current_provider]
        return {
            "status": "healthy",
            "provider": current_provider,
            "available_providers": available_providers,
            "latency_ms": 0,
            "telemetry": ai_provider.get_telemetry(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unavailable",
            "provider": settings.IMPORT_AI_PROVIDER,
            "available_providers": [],
            "error": str(e),
        }


# ============================================================================
# Mapping Suggestion Endpoints
# ============================================================================


class MappingSuggestRequest(BaseModel):
    """Request to suggest column mappings."""

    headers: list[str] = Field(..., description="Column headers from the file")
    sample_rows: list[list[Any]] | None = Field(None, description="Sample data rows for context")
    doc_type: str = Field(
        "products", description="Document type: products, bank_transactions, invoices, expenses"
    )
    use_ai: bool = Field(True, description="Whether to use AI if available")


class MappingSuggestResponse(BaseModel):
    """Response with mapping suggestions."""

    mappings: dict[str, str] = Field(..., description="Suggested mappings {source: target}")
    transforms: dict[str, str] | None = Field(None, description="Suggested transforms per column")
    defaults: dict[str, Any] | None = Field(None, description="Default values for missing fields")
    confidence: float = Field(..., description="Confidence score 0-1")
    reasoning: str = Field(..., description="Explanation of the suggestion")
    from_cache: bool = Field(False, description="Whether result came from cache")
    provider: str = Field(..., description="Provider used: heuristics, openai, etc.")


@router.post("/mappings/suggest", response_model=MappingSuggestResponse)
async def suggest_mapping(
    request: MappingSuggestRequest,
    tenant_id: str | None = Query(None, description="Tenant ID for cache scoping"),
):
    """
    Suggest column mappings using AI or heuristics.

    Endpoint: POST /imports/ai/mappings/suggest

    Uses AI (OpenAI/Azure) if available and enabled, otherwise falls back
    to pattern-based heuristics. Results are cached for performance.

    Args:
        headers: Column headers from the uploaded file
        sample_rows: Optional sample data for better AI suggestions
        doc_type: Type of document (products, bank_transactions, invoices, expenses)
        use_ai: Whether to attempt AI suggestion
        tenant_id: Optional tenant ID for cache scoping

    Returns:
        MappingSuggestResponse with suggested mappings and confidence
    """
    try:
        suggestion = await mapping_suggester.suggest_mapping(
            headers=request.headers,
            sample_rows=request.sample_rows,
            doc_type=request.doc_type,
            tenant_id=tenant_id,
            use_ai=request.use_ai,
        )

        logger.info(
            f"Mapping suggestion: {len(suggestion.mappings)} mappings, "
            f"confidence={suggestion.confidence:.0%}, "
            f"provider={suggestion.provider}, "
            f"cached={suggestion.from_cache}"
        )

        return MappingSuggestResponse(
            mappings=suggestion.mappings,
            transforms=suggestion.transforms,
            defaults=suggestion.defaults,
            confidence=suggestion.confidence,
            reasoning=suggestion.reasoning,
            from_cache=suggestion.from_cache,
            provider=suggestion.provider,
        )

    except Exception as e:
        logger.error(f"Mapping suggestion error: {e}")
        raise


class MappingCacheStatsResponse(BaseModel):
    """Response with cache statistics."""

    in_memory_entries: int
    redis_available: bool
    redis_entries: int | str | None = None


class MappingFeedbackRequest(BaseModel):
    """Request to record mapping corrections/confirmations."""

    doc_type: str = Field(..., description="Document type context")
    headers: list[str] = Field(default_factory=list, description="Original headers")
    mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Final user-approved mapping {source_header: canonical_field}",
    )
    tenant_id: str | None = Field(None, description="Tenant scope for learning")


@router.post("/mappings/feedback")
async def record_mapping_feedback(
    request: MappingFeedbackRequest,
):
    """
    Record explicit mapping feedback for learning.

    Endpoint: POST /imports/ai/mappings/feedback
    """
    try:
        if not request.tenant_id:
            return {"status": "skipped", "message": "tenant_id_required"}

        feedback = MappingFeedback(
            tenant_id=request.tenant_id,
            doc_type=request.doc_type,
            headers=request.headers or list(request.mapping.keys()),
        )
        for source_field, canonical_field in (request.mapping or {}).items():
            if canonical_field and canonical_field != "ignore":
                feedback.mark_field_correct(source_field, canonical_field, confidence=0.9)

        if feedback.field_feedbacks:
            mapping_learner.record_feedback(feedback)
            return {
                "status": "ok",
                "learned_fields": len(feedback.field_feedbacks),
                "doc_type": request.doc_type,
            }
        return {"status": "skipped", "message": "no_valid_fields"}
    except Exception as e:
        logger.error(f"Mapping feedback error: {e}")
        raise


@router.get("/mappings/cache/stats", response_model=MappingCacheStatsResponse)
async def get_mapping_cache_stats():
    """
    Get mapping cache statistics.

    Endpoint: GET /imports/ai/mappings/cache/stats

    Returns:
        Cache statistics including entry counts
    """
    stats = mapping_suggester.get_stats()
    return MappingCacheStatsResponse(**stats)


@router.post("/mappings/cache/clear")
async def clear_mapping_cache(
    tenant_id: str | None = Query(None, description="Clear only for specific tenant"),
):
    """
    Clear mapping suggestion cache.

    Endpoint: POST /imports/ai/mappings/cache/clear

    Args:
        tenant_id: Optional tenant ID to clear only that tenant's cache

    Returns:
        Confirmation message
    """
    mapping_suggester.clear_cache(tenant_id=tenant_id)
    return {
        "status": "ok",
        "message": f"Mapping cache cleared{f' for tenant {tenant_id}' if tenant_id else ''}",
    }
