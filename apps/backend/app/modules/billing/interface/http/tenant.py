"""Billing — Subscription management endpoints."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls, tenant_id_from_request

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/billing",
    tags=["Billing"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


# --- Schemas ---


class PlanOut(BaseModel):
    id: str
    name: str
    display_name: str | None
    price_monthly: float
    price_yearly: float | None
    max_users: int
    max_branches: int
    included_modules: list[str]
    features: dict[str, Any]


class SubscriptionOut(BaseModel):
    id: str
    plan: PlanOut | None
    status: str
    billing_cycle: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    trial_ends_at: datetime | None
    canceled_at: datetime | None


class SubscribeIn(BaseModel):
    plan_id: str
    billing_cycle: str = Field(default="monthly", pattern="^(monthly|yearly)$")


class ChangePlanIn(BaseModel):
    new_plan_id: str
    billing_cycle: str | None = None


# --- Endpoints ---


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    """Lista los planes de suscripción disponibles."""
    rows = db.execute(
        text(
            "SELECT id, name, display_name, price_monthly, price_yearly, "
            "max_users, max_branches, included_modules, features "
            "FROM subscription_plans WHERE is_active = true "
            "ORDER BY sort_order ASC"
        )
    ).fetchall()

    return [
        {
            "id": str(r[0]),
            "name": r[1],
            "display_name": r[2],
            "price_monthly": float(r[3] or 0),
            "price_yearly": float(r[4]) if r[4] else None,
            "max_users": r[5] or 1,
            "max_branches": r[6] or 1,
            "included_modules": list(r[7] or []),
            "features": dict(r[8] or {}),
        }
        for r in rows
    ]


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_current_subscription(request: Request, db: Session = Depends(get_db)):
    """Obtiene la suscripción activa del tenant."""
    tenant_id = tenant_id_from_request(request)

    row = db.execute(
        text(
            "SELECT ts.id, ts.status, ts.billing_cycle, "
            "ts.current_period_start, ts.current_period_end, "
            "ts.trial_ends_at, ts.canceled_at, "
            "sp.id AS plan_id, sp.name, sp.display_name, "
            "sp.price_monthly, sp.price_yearly, "
            "sp.max_users, sp.max_branches, sp.included_modules, sp.features "
            "FROM tenant_subscriptions ts "
            "JOIN subscription_plans sp ON sp.id = ts.plan_id "
            "WHERE ts.tenant_id = :tid AND ts.status IN ('active', 'trialing') "
            "ORDER BY ts.created_at DESC LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    ).first()

    if not row:
        return None

    return {
        "id": str(row[0]),
        "status": row[1],
        "billing_cycle": row[2],
        "current_period_start": row[3],
        "current_period_end": row[4],
        "trial_ends_at": row[5],
        "canceled_at": row[6],
        "plan": {
            "id": str(row[7]),
            "name": row[8],
            "display_name": row[9],
            "price_monthly": float(row[10] or 0),
            "price_yearly": float(row[11]) if row[11] else None,
            "max_users": row[12] or 1,
            "max_branches": row[13] or 1,
            "included_modules": list(row[14] or []),
            "features": dict(row[15] or {}),
        },
    }


@router.post("/subscribe", response_model=dict[str, Any], status_code=201)
def subscribe(payload: SubscribeIn, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva suscripción para el tenant."""
    tenant_id = tenant_id_from_request(request)

    # Check plan exists
    plan = db.execute(
        text(
            "SELECT id, name, price_monthly, price_yearly FROM subscription_plans WHERE id = :pid AND is_active = true"
        ),
        {"pid": payload.plan_id},
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="plan_not_found")

    # Check no active subscription
    existing = db.execute(
        text(
            "SELECT id FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing')"
        ),
        {"tid": str(tenant_id)},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="active_subscription_exists")

    now = datetime.now(UTC)
    from dateutil.relativedelta import relativedelta

    if payload.billing_cycle == "yearly":
        period_end = now + relativedelta(years=1)
    else:
        period_end = now + relativedelta(months=1)

    row = db.execute(
        text(
            "INSERT INTO tenant_subscriptions("
            "tenant_id, plan_id, status, billing_cycle, "
            "current_period_start, current_period_end, trial_ends_at"
            ") VALUES ("
            ":tid, :pid, 'trialing', :cycle, :start, :end, :trial_end"
            ") RETURNING id"
        ),
        {
            "tid": str(tenant_id),
            "pid": payload.plan_id,
            "cycle": payload.billing_cycle,
            "start": now,
            "end": period_end,
            "trial_end": now + relativedelta(days=14),
        },
    ).first()

    db.commit()

    return {
        "subscription_id": str(row[0]),
        "plan": plan[1],
        "status": "trialing",
        "billing_cycle": payload.billing_cycle,
        "trial_ends_at": (now + relativedelta(days=14)).isoformat(),
    }


@router.post("/change-plan", response_model=dict[str, Any])
def change_plan(payload: ChangePlanIn, request: Request, db: Session = Depends(get_db)):
    """Cambia el plan de la suscripción activa (upgrade/downgrade)."""
    tenant_id = tenant_id_from_request(request)

    current = db.execute(
        text(
            "SELECT id, plan_id, billing_cycle FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing') "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    ).first()
    if not current:
        raise HTTPException(status_code=404, detail="no_active_subscription")

    new_plan = db.execute(
        text("SELECT id, name FROM subscription_plans WHERE id = :pid AND is_active = true"),
        {"pid": payload.new_plan_id},
    ).first()
    if not new_plan:
        raise HTTPException(status_code=404, detail="plan_not_found")

    if str(current[1]) == payload.new_plan_id:
        raise HTTPException(status_code=400, detail="already_on_this_plan")

    cycle = payload.billing_cycle or current[2]
    db.execute(
        text(
            "UPDATE tenant_subscriptions SET plan_id = :pid, billing_cycle = :cycle, updated_at = NOW() "
            "WHERE id = :sid"
        ),
        {"pid": payload.new_plan_id, "cycle": cycle, "sid": str(current[0])},
    )
    db.commit()

    return {
        "subscription_id": str(current[0]),
        "new_plan": new_plan[1],
        "billing_cycle": cycle,
        "status": "updated",
    }


@router.post("/cancel", response_model=dict[str, Any])
def cancel_subscription(request: Request, db: Session = Depends(get_db)):
    """Cancela la suscripción activa del tenant."""
    tenant_id = tenant_id_from_request(request)

    current = db.execute(
        text(
            "SELECT id, current_period_end FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing') "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": str(tenant_id)},
    ).first()
    if not current:
        raise HTTPException(status_code=404, detail="no_active_subscription")

    db.execute(
        text(
            "UPDATE tenant_subscriptions SET status = 'canceled', canceled_at = NOW(), updated_at = NOW() "
            "WHERE id = :sid"
        ),
        {"sid": str(current[0])},
    )
    db.commit()

    return {
        "subscription_id": str(current[0]),
        "status": "canceled",
        "access_until": current[1].isoformat() if current[1] else None,
    }


@router.post("/webhook/stripe", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook para eventos de Stripe (subscription lifecycle)."""
    stripe_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not stripe_secret:
        raise HTTPException(status_code=500, detail="stripe_webhook_not_configured")

    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        import stripe

        event = stripe.Webhook.construct_event(body, sig, stripe_secret)
    except Exception as e:
        logger.warning("Stripe webhook verification failed: %s", e)
        raise HTTPException(status_code=400, detail="invalid_signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})

    if event_type == "customer.subscription.updated":
        stripe_sub_id = data.get("id")
        status_map = {
            "active": "active",
            "past_due": "past_due",
            "canceled": "canceled",
            "trialing": "trialing",
            "unpaid": "past_due",
        }
        new_status = status_map.get(data.get("status"), data.get("status"))
        db.execute(
            text(
                "UPDATE tenant_subscriptions SET status = :st, updated_at = NOW() "
                "WHERE stripe_subscription_id = :sid"
            ),
            {"st": new_status, "sid": stripe_sub_id},
        )
        db.commit()

    elif event_type == "customer.subscription.deleted":
        stripe_sub_id = data.get("id")
        db.execute(
            text(
                "UPDATE tenant_subscriptions SET status = 'canceled', canceled_at = NOW(), updated_at = NOW() "
                "WHERE stripe_subscription_id = :sid"
            ),
            {"sid": stripe_sub_id},
        )
        db.commit()

    return {"received": True}
