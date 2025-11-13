from __future__ import annotations

from celery import shared_task
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
                INSERT INTO sri_submissions(invoice_id, status)
                VALUES (:iid, 'PENDING')
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
                INSERT INTO sii_batches(period, status)
                VALUES (:p, 'PENDING')
                RETURNING id
                """
            ),
            {"p": period},
        )
        batch_id = res.scalar()
        # For demo, mark accepted
        db.execute(
            text("UPDATE sii_batches SET status='ACCEPTED' WHERE id=:id"),
            {"id": batch_id},
        )
        db.commit()
    return {"batch_id": str(batch_id), "status": "ACCEPTED"}


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.scheduled_build_sii")
def scheduled_build_sii() -> dict:
    """
    Beat-friendly task: computes period based on environment and enqueues a single-tenant SII build.

    Env vars:
      - EINV_SII_PERIOD_MODE: 'monthly' (YYYYMM), 'quarterly' (YYYYQn), default 'monthly'
      - EINV_TENANT_ID: tenant UUID to use (required)
    """
    import os
    from datetime import datetime

    tenant_id = os.getenv("EINV_TENANT_ID")
    if not tenant_id:
        return {"skipped": True, "reason": "EINV_TENANT_ID not set"}

    mode = (os.getenv("EINV_SII_PERIOD_MODE") or "monthly").lower()
    now = datetime.utcnow()
    if mode == "quarterly":
        q = (now.month - 1) // 3 + 1
        period = f"{now.year}Q{q}"
    else:
        period = f"{now.year}{now.month:02d}"

    # run synchronously in this task to keep logs together
    return build_and_send_sii(period, tenant_id)


@shared_task(name="apps.backend.app.modules.einvoicing.tasks.scheduled_retry")
def scheduled_retry() -> dict:
    """
    Retry loop for SRI/SII errors for a single tenant.

    Env vars:
      - EINV_TENANT_ID: tenant UUID (required)
      - EINV_RETRY_MAX: max items per run (default 25)
      - EINV_SII_PERIOD_MODE: 'monthly'|'quarterly' (default 'monthly') for SII rebuild
    """
    import os
    from datetime import datetime

    tenant_id = os.getenv("EINV_TENANT_ID")
    if not tenant_id:
        return {"skipped": True, "reason": "EINV_TENANT_ID not set"}

    max_items = int(os.getenv("EINV_RETRY_MAX", "25") or 25)

    retried_sri: int = 0
    retried_sii: int = 0

    # SRI: find failed submissions and re-send
    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
        sri_rows = db.execute(
            text(
                """
                SELECT DISTINCT invoice_id
                FROM sri_submissions
                WHERE status IN ('ERROR','REJECTED')
                ORDER BY updated_at DESC
                LIMIT :lim
                """
            ).bindparams(lim=max_items)
        ).fetchall()

    for r in sri_rows:
        try:
            sign_and_send(int(r[0]), tenant_id)
            retried_sri += 1
        except Exception:
            # keep looping
            pass

    # SII: rebuild batch for current period (idempotent in our stub)
    mode = (os.getenv("EINV_SII_PERIOD_MODE") or "monthly").lower()
    now = datetime.utcnow()
    if mode == "quarterly":
        q = (now.month - 1) // 3 + 1
        period = f"{now.year}Q{q}"
    else:
        period = f"{now.year}{now.month:02d}"
    try:
        build_and_send_sii(period, tenant_id)
        retried_sii = 1
    except Exception:
        retried_sii = 0

    return {"sri_retried": retried_sri, "sii_retried": retried_sii}
