"""OCR Metrics HTTP Endpoint.

Exposes OCR worker metrics via REST API for monitoring and alerting systems.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.imports.monitoring import (
    get_all_metrics,
    get_tenant_metrics,
)


class QueueMetrics(BaseModel):
    pending: int
    running: int
    done: int
    failed: int
    total: int
    oldest_pending_age_seconds: float | None
    avg_wait_time_seconds: float | None


class ProcessingMetrics(BaseModel):
    p50_ms: float | None
    p95_ms: float | None
    p99_ms: float | None


class RateMetrics(BaseModel):
    success_rate: float
    error_rate: float
    jobs_per_minute: float


class TotalMetrics(BaseModel):
    total_processed: int
    total_failed: int
    uptime_seconds: float


class HealthStatus(BaseModel):
    queue_healthy: bool
    error_rate_healthy: bool
    backlog_age_healthy: bool


class OCRMetricsResponse(BaseModel):
    timestamp: str
    queue: QueueMetrics
    processing_times: ProcessingMetrics
    rates: RateMetrics
    totals: TotalMetrics
    health: HealthStatus


class TenantQueueCounts(BaseModel):
    pending: int
    running: int
    done: int
    failed: int


class TenantMetricsResponse(BaseModel):
    tenant_id: str
    timestamp: str
    all_time: TenantQueueCounts
    last_24h: TenantQueueCounts


router = APIRouter(
    prefix="/imports/ocr",
    tags=["OCR Metrics"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get(
    "/metrics",
    response_model=OCRMetricsResponse,
    summary="Get OCR worker metrics",
    description="""
    Returns comprehensive OCR worker metrics including:
    - Queue depths (pending, running, done, failed jobs)
    - Processing times (p50, p95, p99 percentiles)
    - Success/error rates
    - Health indicators for alerting
    
    Metrics are aggregated across all tenants for system-wide monitoring.
    Processing time percentiles are calculated from a sliding window of recent jobs.
    """,
)
async def get_ocr_metrics(db: Session = Depends(get_db)) -> OCRMetricsResponse:
    """Get global OCR processing metrics."""
    metrics = get_all_metrics(db)
    return OCRMetricsResponse(**metrics)


@router.get(
    "/metrics/tenant",
    response_model=TenantMetricsResponse,
    summary="Get tenant-specific OCR metrics",
    description="""
    Returns OCR metrics scoped to the current tenant.
    Includes all-time and last 24h job counts by status.
    """,
)
async def get_tenant_ocr_metrics(
    request: Request,
    db: Session = Depends(get_db),
) -> TenantMetricsResponse:
    """Get OCR metrics for the current tenant."""
    claims = getattr(request.state, "access_claims", {})
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant ID not found in claims",
        )
    
    metrics = get_tenant_metrics(db, tenant_id)
    return TenantMetricsResponse(**metrics)
