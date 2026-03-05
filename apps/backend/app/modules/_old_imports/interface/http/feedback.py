"""Feedback endpoints for classification corrections tracking."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.core.access_guard import with_access_claims
from app.modules.imports.services.feedback_service import feedback_service
from app.modules.imports.services.header_classifier import header_classifier

logger = logging.getLogger("app.imports.feedback")

router = APIRouter(
    prefix="/feedback",
    tags=["Imports Feedback"],
    dependencies=[Depends(with_access_claims)],
)


class RecordFeedbackRequest(BaseModel):
    """Request para registrar feedback de clasificación."""

    batch_id: str | None = None
    decision_log_id: str | None = None
    original_parser: str
    original_confidence: float
    original_doc_type: str = "unknown"
    corrected_parser: str | None = None
    corrected_doc_type: str | None = None
    was_correct: bool
    headers: list[str]
    filename: str


class FeedbackResponse(BaseModel):
    """Response del registro de feedback."""

    id: str
    message: str
    was_correct: bool


class AccuracyStatsResponse(BaseModel):
    """Response con estadísticas de precisión."""

    total_classifications: int
    correct_count: int
    corrected_count: int
    accuracy_rate: float
    by_doc_type: dict[str, dict[str, Any]]
    most_corrected_parsers: list[dict[str, Any]]


class RetrainResponse(BaseModel):
    """Response del reentrenamiento."""

    success: bool
    message: str
    samples_used: int


def _get_tenant_id(request: Request) -> str:
    """Extract tenant_id from request."""
    access_claims = getattr(request.state, "access_claims", None)
    if not access_claims:
        raise HTTPException(status_code=401, detail="No access claims")
    return access_claims.get("tenant_id", "unknown")


@router.post("", response_model=FeedbackResponse)
async def record_feedback(
    request: Request,
    body: RecordFeedbackRequest,
) -> FeedbackResponse:
    """Registra feedback de clasificación."""
    tenant_id = _get_tenant_id(request)

    try:
        entry = feedback_service.record_feedback(
            tenant_id=tenant_id,
            original_parser=body.original_parser,
            original_confidence=body.original_confidence,
            original_doc_type=body.original_doc_type,
            corrected_parser=body.corrected_parser,
            corrected_doc_type=body.corrected_doc_type,
            was_correct=body.was_correct,
            headers=body.headers,
            filename=body.filename,
            decision_log_id=body.decision_log_id,
        )

        logger.info(
            f"Feedback recorded: tenant={tenant_id}, "
            f"was_correct={body.was_correct}, "
            f"original={body.original_parser}, "
            f"corrected={body.corrected_parser}"
        )

        return FeedbackResponse(
            id=entry.id,
            message="Feedback registrado exitosamente",
            was_correct=body.was_correct,
        )

    except Exception as e:
        logger.exception(f"Error recording feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al registrar feedback: {str(e)}",
        )


@router.get("/stats", response_model=AccuracyStatsResponse)
async def get_accuracy_stats(
    request: Request,
    all_tenants: bool = False,
) -> AccuracyStatsResponse:
    """Obtiene estadísticas de precisión."""
    tenant_id = _get_tenant_id(request) if not all_tenants else None

    try:
        stats = feedback_service.get_accuracy_stats(tenant_id=tenant_id)
        return AccuracyStatsResponse(**stats)
    except Exception as e:
        logger.exception(f"Error getting accuracy stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}",
        )


@router.post("/retrain", response_model=RetrainResponse)
async def trigger_retraining(request: Request) -> RetrainResponse:
    """Dispara reentrenamiento del modelo con el feedback acumulado."""
    tenant_id = _get_tenant_id(request)

    try:
        training_data = feedback_service.get_training_data(min_entries=10)

        if not training_data:
            return RetrainResponse(
                success=False,
                message="No hay suficientes datos de feedback para reentrenar (mínimo 10)",
                samples_used=0,
            )

        success = header_classifier.train(training_data)

        if success:
            logger.info(
                f"Model retrained with {len(training_data)} samples, "
                f"triggered by tenant={tenant_id}"
            )
            return RetrainResponse(
                success=True,
                message=f"Modelo reentrenado exitosamente con {len(training_data)} ejemplos",
                samples_used=len(training_data),
            )
        else:
            return RetrainResponse(
                success=False,
                message="Reentrenamiento falló. scikit-learn puede no estar disponible.",
                samples_used=0,
            )

    except Exception as e:
        logger.exception(f"Error triggering retraining: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al reentrenar modelo: {str(e)}",
        )


@router.get("/export")
async def export_training_data(request: Request) -> dict[str, Any]:
    """Exporta datos de feedback para análisis o reentrenamiento externo."""
    _get_tenant_id(request)

    try:
        return feedback_service.export_for_retraining()
    except Exception as e:
        logger.exception(f"Error exporting training data: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar datos: {str(e)}",
        )
