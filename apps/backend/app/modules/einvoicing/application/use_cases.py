from uuid import UUID
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status

from app.config.database import get_db_session
from app.workers.einvoicing_tasks import sign_and_send_sri_task, sign_and_send_facturae_task
from app.models.core.einvoicing import SRISubmission, SIIBatch, SIIBatchItem
from app.schemas.einvoicing import EinvoicingStatusResponse

class EinvoicingTaskResult:
    def __init__(self, task_id: str):
        self.task_id = task_id

async def send_einvoice_use_case(
    tenant_id: UUID, invoice_id: UUID, country: str
) -> EinvoicingTaskResult:
    """
    Initiates the e-invoicing process by triggering the appropriate Celery task.
    """
    if country.upper() == "EC":
        task = sign_and_send_sri_task.delay(str(invoice_id), str(tenant_id))
    elif country.upper() == "ES":
        task = sign_and_send_facturae_task.delay(str(invoice_id), str(tenant_id))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported country for e-invoicing: {country}",
        )
    return EinvoicingTaskResult(task.id)

async def get_einvoice_status_use_case(
    tenant_id: UUID, invoice_id: UUID
) -> Optional[EinvoicingStatusResponse]:
    """
    Retrieves the status of an e-invoice submission from the database.
    Handles both SRI (EC) and SII (ES) submissions.
    """
    async with get_db_session() as db:
        # First try SRI submissions (Ecuador)
        sri_result = await db.execute(
            select(SRISubmission).where(
                SRISubmission.tenant_id == tenant_id,
                SRISubmission.invoice_id == invoice_id,
            ).order_by(SRISubmission.created_at.desc())
        )
        sri_submission = sri_result.scalars().first()

        if sri_submission:
            return EinvoicingStatusResponse(
                invoice_id=invoice_id,  # Convert to UUID for response
                status=sri_submission.status,
                clave_acceso=sri_submission.receipt_number,  # SRI uses receipt_number
                error_message=sri_submission.error_message,
                submitted_at=sri_submission.created_at,
                created_at=sri_submission.created_at,
            )

        # If not found in SRI, try SII batch items (Spain)
        sii_result = await db.execute(
            select(SIIBatchItem).where(
                SIIBatchItem.tenant_id == tenant_id,
                SIIBatchItem.invoice_id == invoice_id,
            ).order_by(SIIBatchItem.created_at.desc())
        )
        sii_item = sii_result.scalars().first()

        if sii_item:
            return EinvoicingStatusResponse(
                invoice_id=invoice_id,
                status=sii_item.status,
                clave_acceso=None,  # SII doesn't use clave_acceso like SRI
                error_message=sii_item.error_message,
                submitted_at=sii_item.created_at,
                created_at=sii_item.created_at,
            )

        return None
