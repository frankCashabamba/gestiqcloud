from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.modules.einvoicing.application.use_cases import (
    get_einvoice_status_use_case,
    send_einvoice_use_case,
)
from app.schemas.einvoicing import EinvoicingSendRequest, EinvoicingStatusResponse

router = APIRouter(
    prefix="/einvoicing",
    tags=["Einvoicing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant"))],
)


class EinvoicingSendResponse(BaseModel):
    message: str
    task_id: str


@router.post("/send", response_model=EinvoicingSendResponse)
async def send_einvoice(
    payload: EinvoicingSendRequest,
    claims: dict = Depends(with_access_claims),
) -> EinvoicingSendResponse:
    tenant_id = claims.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id_missing")
    task_result = await send_einvoice_use_case(tenant_id, payload.invoice_id, payload.country)
    return EinvoicingSendResponse(
        message="E-invoice processing initiated", task_id=task_result.task_id
    )


@router.get("/status/{invoice_id}", response_model=EinvoicingStatusResponse)
async def get_einvoice_status(
    invoice_id: UUID,
    claims: dict = Depends(with_access_claims),
) -> EinvoicingStatusResponse:
    tenant_id = claims.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id_missing")
    status_result = await get_einvoice_status_use_case(tenant_id, invoice_id)
    if not status_result:
        raise HTTPException(status_code=404, detail="E-invoice status not found")
    return status_result
