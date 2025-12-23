"""
Endpoint POST /imports/batches/{batch_id}/confirm para confirmar parser de un batch.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.models.core.modelsimport import ImportBatch, ImportMapping

logger = logging.getLogger("app.imports.confirm")

router = APIRouter(
    prefix="/batches",
    tags=["Imports Confirm"],
    dependencies=[Depends(with_access_claims)],
)


class ConfirmBatchRequest(BaseModel):
    """Request para confirmar parser de un batch."""

    parser_id: str
    mapping_id: str | None = None
    custom_mapping: dict[str, str] | None = None
    transforms: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None


class ConfirmBatchResponse(BaseModel):
    """Respuesta de confirmación."""

    batch_id: str
    confirmed_parser: str
    mapping_applied: bool
    ready_to_process: bool
    message: str


def _get_claims(request: Request) -> dict[str, Any]:
    """Extract access claims from request."""
    access_claims = getattr(request.state, "access_claims", None)
    if not access_claims:
        raise HTTPException(status_code=401, detail="No access claims")
    return access_claims


@router.post("/{batch_id}/confirm", response_model=ConfirmBatchResponse)
async def confirm_batch(
    batch_id: str,
    request_body: ConfirmBatchRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Confirma el parser y mapping para un batch que requiere confirmación.

    - Actualiza el batch con el parser confirmado
    - Aplica el mapping (template o custom)
    - Marca como listo para procesar
    - Registra si hubo override del usuario
    """
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id requerido")

    try:
        batch_uuid = UUID(batch_id)
        tenant_uuid = UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de batch inválido")

    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_uuid, ImportBatch.tenant_id == tenant_uuid)
        .first()
    )

    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")

    if not batch.requires_confirmation:
        raise HTTPException(
            status_code=400,
            detail="Este batch no requiere confirmación (confianza suficiente)",
        )

    if batch.confirmed_at:
        raise HTTPException(status_code=400, detail="Este batch ya fue confirmado")

    user_override = batch.suggested_parser != request_body.parser_id

    mapping_applied = False
    if request_body.mapping_id:
        try:
            mapping_uuid = UUID(request_body.mapping_id)
            mapping = (
                db.query(ImportMapping)
                .filter(
                    ImportMapping.id == mapping_uuid,
                    ImportMapping.tenant_id == tenant_uuid,
                )
                .first()
            )
            if mapping:
                batch.mapping_id = mapping_uuid
                mapping_applied = True
            else:
                logger.warning(f"Mapping {request_body.mapping_id} not found")
        except ValueError:
            logger.warning(f"Invalid mapping_id: {request_body.mapping_id}")
    elif request_body.custom_mapping:
        mapping_applied = True

    batch.confirmed_parser = request_body.parser_id
    batch.parser_id = request_body.parser_id
    batch.confirmed_at = datetime.utcnow()
    batch.user_override = user_override
    batch.requires_confirmation = False

    db.commit()

    logger.info(
        f"Batch {batch_id} confirmed: parser={request_body.parser_id}, "
        f"user_override={user_override}, mapping_applied={mapping_applied}, "
        f"tenant_id={tenant_id}"
    )

    return ConfirmBatchResponse(
        batch_id=str(batch.id),
        confirmed_parser=request_body.parser_id,
        mapping_applied=mapping_applied,
        ready_to_process=True,
        message="Batch confirmado y listo para procesar"
        + (" (parser diferente al sugerido)" if user_override else ""),
    )


@router.get("/{batch_id}/confirmation-status")
async def get_confirmation_status(
    batch_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Obtiene el estado de confirmación de un batch.
    """
    claims = _get_claims(request)
    tenant_id = claims.get("tenant_id")

    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id requerido")

    try:
        batch_uuid = UUID(batch_id)
        tenant_uuid = UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de batch inválido")

    batch = (
        db.query(ImportBatch)
        .filter(ImportBatch.id == batch_uuid, ImportBatch.tenant_id == tenant_uuid)
        .first()
    )

    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado")

    return {
        "batch_id": str(batch.id),
        "requires_confirmation": batch.requires_confirmation,
        "confirmed_at": batch.confirmed_at.isoformat() if batch.confirmed_at else None,
        "confirmed_parser": batch.confirmed_parser,
        "suggested_parser": batch.suggested_parser,
        "classification_confidence": batch.classification_confidence,
        "user_override": batch.user_override,
    }
