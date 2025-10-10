from __future__ import annotations

from celery import shared_task
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config.database import SessionLocal


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.sign_and_send")
def sign_and_send(invoice_id: int, tenant_id: str | None = None) -> dict:
    """
    Stub: signs and sends an invoice to SRI (Ecuador) asynchronously.
    Updates sri_submissions table with simulated status.
    """
    with SessionLocal() as db:
        # Scope tenant context for RLS
        if tenant_id:
            db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        # Insert PENDING submission if not exists
        db.execute(
            text(
                """
                INSERT INTO sri_submissions(tenant_id, invoice_id, status)
                VALUES (current_setting('app.tenant_id', true)::uuid, :iid, 'PENDING')
                ON CONFLICT DO NOTHING
                """
            ),
            {"iid": invoice_id},
        )
        # Simulate success
        db.execute(
            text(
                """
                UPDATE sri_submissions
                   SET status='AUTHORIZED', authorization_number = gen_random_uuid()::text
                 WHERE invoice_id=:iid
                """
            ),
            {"iid": invoice_id},
        )
        db.commit()
    return {"invoice_id": invoice_id, "status": "AUTHORIZED"}


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.build_and_send_sii")
def build_and_send_sii(period: str, tenant_id: str | None = None) -> dict:
    """
    Stub: builds a SII batch for Spain and marks as ACCEPTED.
    """
    with SessionLocal() as db:
        if tenant_id:
            db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        res = db.execute(
            text(
                """
                INSERT INTO sii_batches(tenant_id, period, status)
                VALUES (current_setting('app.tenant_id', true)::uuid, :p, 'PENDING')
                RETURNING id
                """
            ),
            {"p": period},
        )
        batch_id = res.scalar()
        # For demo, mark accepted
        db.execute(
            text("UPDATE sii_batches SET status='ACCEPTED' WHERE id=:id"), {"id": batch_id}
        )
        db.commit()
    return {"batch_id": str(batch_id), "status": "ACCEPTED"}
