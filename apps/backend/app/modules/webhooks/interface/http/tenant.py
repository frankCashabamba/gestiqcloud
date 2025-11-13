from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import tenant_id_from_request
from app.config.database import get_db
from app.db.rls import ensure_rls

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
    secret: Optional[str] = None


@router.post("/subscriptions", response_model=dict)
def create_subscription(payload: SubCreate, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            "INSERT INTO webhook_subscriptions(event, url, secret) VALUES (:e, :u, :s) RETURNING id"
        ),
        {"e": payload.event, "u": payload.url, "s": payload.secret},
    ).first()
    db.commit()
    return {"id": str(row[0])}


@router.get("/subscriptions", response_model=list[dict])
def list_subscriptions(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT id::text AS id, event, url, active, created_at FROM webhook_subscriptions"
        )
    )
    return [dict(r) for r in rows.mappings().all()]


class DeliverIn(BaseModel):
    event: str
    payload: dict


@router.post("/deliveries", response_model=dict)
def enqueue_delivery(payload: DeliverIn, request: Request, db: Session = Depends(get_db)):
    # Enqueue one delivery per active subscription  
    _tid = tenant_id_from_request(request)
    subs = db.execute(
        text("SELECT id, url FROM webhook_subscriptions WHERE event=:e AND active"),
        {"e": payload.event},
    ).fetchall()
    if not subs:
        return {"enqueued": 0}
    count = 0
    for _ in subs:
        row = db.execute(
            text(
                "INSERT INTO webhook_deliveries(event, payload, target_url, status) VALUES (:e, :p::jsonb, :u, 'PENDING') RETURNING id"
            ),
            {"e": payload.event, "p": payload.payload, "u": _[1]},
        ).first()
        count += 1
        if celery_app:
            celery_app.send_task(
                "apps.backend.app.modules.webhooks.tasks.deliver", args=[str(row[0])]
            )
    db.commit()
    return {"enqueued": count}
