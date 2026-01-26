"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from app.telemetry.metrics import get_content_type, get_metrics

router = APIRouter(tags=["Observability"])


@router.get("/metrics", include_in_schema=False)
async def prometheus_metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(content=get_metrics(), media_type=get_content_type())
