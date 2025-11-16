from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_active_tenant_user
from app.modules.einvoicing.application.use_cases import (
    get_einvoice_status_use_case,
    send_einvoice_use_case,
)
from app.schemas.einvoicing import EinvoicingSendRequest, EinvoicingStatusResponse

router = APIRouter(prefix="/einvoicing", tags=["Einvoicing"])


class EinvoicingSendResponse(BaseModel):
    message: str
    task_id: str


@router.post("/send", response_model=EinvoicingSendResponse)
async def send_einvoice(
    payload: EinvoicingSendRequest,
    user=Depends(get_current_active_tenant_user),
) -> EinvoicingSendResponse:
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id_missing")
    task_result = await send_einvoice_use_case(tenant_id, payload.invoice_id, payload.country)
    return EinvoicingSendResponse(
        message="E-invoice processing initiated", task_id=task_result.task_id
    )


@router.get("/status/{invoice_id}", response_model=EinvoicingStatusResponse)
async def get_einvoice_status(
    invoice_id: UUID,
    user=Depends(get_current_active_tenant_user),
) -> EinvoicingStatusResponse:
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant_id_missing")
    status_result = await get_einvoice_status_use_case(tenant_id, invoice_id)
    if not status_result:
        raise HTTPException(status_code=404, detail="E-invoice status not found")
    return status_result
