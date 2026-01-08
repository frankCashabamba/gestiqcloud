from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_from_request

try:
    from apps.backend.celery_app import celery_app
except Exception:
    celery_app = None


router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


class SubCreate(BaseModel):
    event: str
    url: str
    secret: str | None = None


@router.post("/subscriptions", response_model=dict)
def create_subscription(payload: SubCreate, request: Request, db: Session = Depends(get_db)):
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    row = db.execute(
        text(
            "INSERT INTO webhook_subscriptions(tenant_id, event, url, secret) "
            "VALUES (:tid, :e, :u, :s) RETURNING id"
        ),
        {"tid": tenant_id, "e": payload.event, "u": payload.url, "s": payload.secret},
    ).first()
    db.commit()
    return {"id": str(row[0])}


@router.get("/subscriptions", response_model=list[dict])
def list_subscriptions(request: Request, db: Session = Depends(get_db)):
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    rows = db.execute(
        text(
            "SELECT id::text AS id, event, url, active, created_at "
            "FROM webhook_subscriptions WHERE tenant_id=:tid"
        ),
        {"tid": tenant_id},
    )
    return [dict(r) for r in rows.mappings().all()]


class DeliverIn(BaseModel):
    event: str
    payload: dict


@router.post("/deliveries", response_model=dict)
def enqueue_delivery(payload: DeliverIn, request: Request, db: Session = Depends(get_db)):
    # Enqueue one delivery per active subscription
    tenant_id = tenant_id_from_request(request)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    subs = db.execute(
        text(
            "SELECT id, url FROM webhook_subscriptions "
            "WHERE tenant_id=:tid AND event=:e AND active"
        ),
        {"tid": tenant_id, "e": payload.event},
    ).fetchall()
    if not subs:
        return {"enqueued": 0}
    count = 0
    for _ in subs:
        row = db.execute(
            text(
                "INSERT INTO webhook_deliveries(tenant_id, event, payload, target_url, status) "
                "VALUES (:tid, :e, :p::jsonb, :u, 'PENDING') RETURNING id"
            ),
            {"tid": tenant_id, "e": payload.event, "p": payload.payload, "u": _[1]},
        ).first()
        count += 1
        if celery_app:
            celery_app.send_task(
                "apps.backend.app.modules.webhooks.tasks.deliver", args=[str(row[0])]
            )
    db.commit()
    return {"enqueued": count}
