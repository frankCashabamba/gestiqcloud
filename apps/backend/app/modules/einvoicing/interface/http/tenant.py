from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.config.database import get_db
from app.db.rls import ensure_rls

try:
    from apps.backend.celery_app import celery_app  # when root is repo
except Exception:
    celery_app = None

router = APIRouter(
    prefix="/einvoicing",
    tags=["E-invoicing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


class SendIn(BaseModel):
    country: str  # 'EC' or 'ES'
    period: str | None = None  # for ES


@router.post("/send/{invoice_id}", response_model=dict)
def send(invoice_id: int, payload: SendIn, request: Request, db: Session = Depends(get_db)):
    if payload.country == "EC":
        # enqueue SRI task
        if not celery_app:
            # run inline stub
            from app.modules.einvoicing.tasks import sign_and_send

            return sign_and_send(invoice_id)
        r = celery_app.send_task(
            "apps.backend.app.modules.einvoicing.tasks.sign_and_send", args=[invoice_id]
        )
        return {"task_id": r.id}
    elif payload.country == "ES":
        # enqueue SII batch for period
        per = payload.period or "0000Q0"
        if not celery_app:
            from app.modules.einvoicing.tasks import build_and_send_sii

            return build_and_send_sii(per)
        r = celery_app.send_task(
            "apps.backend.app.modules.einvoicing.tasks.build_and_send_sii", args=[per]
        )
        return {"task_id": r.id}
    else:
        raise HTTPException(status_code=400, detail="unsupported_country")


@router.get("/status/{kind}/{ref}", response_model=dict)
def status(kind: str, ref: str, request: Request, db: Session = Depends(get_db)):
    if kind == "sri":
        row = db.execute(
            text("SELECT id::text, status::text, error_message FROM sri_submissions WHERE id::text=:id"),
            {"id": ref},
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="not_found")
        return {"id": row[0], "status": row[1], "error": row[2]}
    if kind == "sii":
        row = db.execute(
            text("SELECT id::text, status::text, error_message FROM sii_batches WHERE id::text=:id"),
            {"id": ref},
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="not_found")
        return {"id": row[0], "status": row[1], "error": row[2]}
    raise HTTPException(status_code=400, detail="unsupported_kind")


class ExplainIn(BaseModel):
    kind: str  # 'sri' or 'sii'
    id: str


@router.post("/explain_error", response_model=dict)
def explain_error(payload: ExplainIn, request: Request, db: Session = Depends(get_db)):
    # Basic explanation based on last error message
    if payload.kind == "sri":
        row = db.execute(
            text("SELECT error_code, error_message FROM sri_submissions WHERE id::text=:id"),
            {"id": payload.id},
        ).first()
    elif payload.kind == "sii":
        row = db.execute(
            text("SELECT error_message FROM sii_batches WHERE id::text=:id"),
            {"id": payload.id},
        ).first()
    else:
        raise HTTPException(status_code=400, detail="unsupported_kind")

    msg = (row[0] if row and row[0] else None) if payload.kind == "sri" else (row[0] if row else None)
    if not msg:
        return {"explanation": "Sin errores registrados"}
    # Placeholder NLP explanation (deterministic)
    return {"explanation": f"Error del proveedor fiscal: {msg}. Revisa credenciales y formato XML."}

