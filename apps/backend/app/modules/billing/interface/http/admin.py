"""Admin billing endpoints for managing tenant subscriptions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import set_tenant_guc
from app.modules.billing.interface.http.tenant import (
    BillingPortalIn,
    ChangePlanIn,
    PlanOut,
    SubscribeIn,
    SubscriptionOut,
)
from app.modules.billing.service import (
    ensure_stripe_customer,
    get_price_id_for_cycle,
    get_stripe_module,
    load_billing_contact,
    load_existing_customer_id,
    load_plan,
    normalize_plan_features,
    normalize_plan_modules,
    resolve_return_url,
    stripe_is_configured,
    stripe_status_to_local,
    sync_subscription_from_stripe,
    unix_to_dt,
)

router = APIRouter(
    prefix="/companies/{tenant_id}/billing",
    tags=["Admin Billing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)

catalog_router = APIRouter(
    prefix="/billing",
    tags=["Admin Billing"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _validate_tenant_id(tenant_id: str) -> str:
    try:
        return str(UUID(str(tenant_id)))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_tenant_id") from exc


def _list_plans(db: Session) -> list[dict[str, Any]]:
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
            "included_modules": normalize_plan_modules(r[7]),
            "features": normalize_plan_features(r[8]),
        }
        for r in rows
    ]


def _get_subscription(db: Session, tenant_id: str) -> dict[str, Any] | None:
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
            "WHERE ts.tenant_id = :tid "
            "ORDER BY ts.created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
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
            "included_modules": normalize_plan_modules(row[14]),
            "features": normalize_plan_features(row[15]),
        },
    }


@catalog_router.get("/plans", response_model=list[PlanOut])
def list_plans_catalog_admin(db: Session = Depends(get_db)):
    return _list_plans(db)


@router.get("/plans", response_model=list[PlanOut])
def list_plans_admin(tenant_id: str, db: Session = Depends(get_db)):
    _validate_tenant_id(tenant_id)
    return _list_plans(db)


@router.get("/subscription", response_model=SubscriptionOut | None)
def get_current_subscription_admin(tenant_id: str, db: Session = Depends(get_db)):
    tenant_id = _validate_tenant_id(tenant_id)
    set_tenant_guc(db, tenant_id, persist=True)
    return _get_subscription(db, tenant_id)


@router.post("/subscribe", response_model=dict[str, Any], status_code=201)
def subscribe_admin(
    tenant_id: str,
    payload: SubscribeIn,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _validate_tenant_id(tenant_id)
    set_tenant_guc(db, tenant_id, persist=True)

    plan = load_plan(db, payload.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan_not_found")

    existing = db.execute(
        text(
            "SELECT id FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing', 'past_due')"
        ),
        {"tid": tenant_id},
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="active_subscription_exists")

    price_id = get_price_id_for_cycle(plan, payload.billing_cycle)
    if stripe_is_configured() and price_id:
        email, company_name = load_billing_contact(db, tenant_id)
        customer_id = ensure_stripe_customer(db, tenant_id, email, company_name)
        return_url = resolve_return_url(
            request, f"/admin/companies/{tenant_id}/config", payload.return_url
        )
        stripe = get_stripe_module()
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            client_reference_id=tenant_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=return_url,
            cancel_url=return_url,
            metadata={
                "tenant_id": tenant_id,
                "plan_id": plan.id,
                "billing_cycle": payload.billing_cycle,
            },
            subscription_data={
                "metadata": {
                    "tenant_id": tenant_id,
                    "plan_id": plan.id,
                    "billing_cycle": payload.billing_cycle,
                }
            },
        )
        return {
            "mode": "stripe_checkout",
            "checkout_url": session.get("url"),
            "session_id": session.get("id"),
            "customer_id": customer_id,
            "billing_cycle": payload.billing_cycle,
            "plan": plan.name,
        }

    from dateutil.relativedelta import relativedelta

    now = datetime.now(UTC)
    period_end = (
        now + relativedelta(years=1)
        if payload.billing_cycle == "yearly"
        else now + relativedelta(months=1)
    )

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
            "tid": tenant_id,
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
        "plan": plan.name,
        "status": "trialing",
        "billing_cycle": payload.billing_cycle,
        "trial_ends_at": (now + relativedelta(days=14)).isoformat(),
        "mode": "local_trial",
    }


@router.post("/change-plan", response_model=dict[str, Any])
def change_plan_admin(tenant_id: str, payload: ChangePlanIn, db: Session = Depends(get_db)):
    tenant_id = _validate_tenant_id(tenant_id)
    set_tenant_guc(db, tenant_id, persist=True)

    current = db.execute(
        text(
            "SELECT id, plan_id, billing_cycle, stripe_subscription_id FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing', 'past_due') "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).first()
    if not current:
        raise HTTPException(status_code=404, detail="no_active_subscription")

    new_plan = load_plan(db, payload.new_plan_id)
    if not new_plan:
        raise HTTPException(status_code=404, detail="plan_not_found")

    if str(current[1]) == payload.new_plan_id:
        raise HTTPException(status_code=400, detail="already_on_this_plan")

    cycle = payload.billing_cycle or current[2]
    stripe_subscription_id = current[3]
    price_id = get_price_id_for_cycle(new_plan, cycle)
    if stripe_subscription_id and stripe_is_configured() and price_id:
        stripe = get_stripe_module()
        subscription = stripe.Subscription.retrieve(stripe_subscription_id)
        items = (subscription.get("items") or {}).get("data") or []
        if not items:
            raise HTTPException(status_code=409, detail="stripe_subscription_items_missing")
        updated = stripe.Subscription.modify(
            stripe_subscription_id,
            items=[{"id": items[0]["id"], "price": price_id}],
            proration_behavior="create_prorations",
            cancel_at_period_end=False,
            metadata={
                "tenant_id": tenant_id,
                "plan_id": new_plan.id,
                "billing_cycle": cycle,
            },
        )
        synced = sync_subscription_from_stripe(
            db,
            tenant_id=tenant_id,
            plan_id=new_plan.id,
            billing_cycle=cycle,
            stripe_subscription=updated,
        )
        return {
            "subscription_id": synced["subscription_id"],
            "new_plan": new_plan.name,
            "billing_cycle": cycle,
            "status": synced["status"],
            "mode": "stripe",
            "stripe_subscription_id": synced["stripe_subscription_id"],
        }

    db.execute(
        text(
            "UPDATE tenant_subscriptions SET plan_id = :pid, billing_cycle = :cycle, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :sid"
        ),
        {"pid": payload.new_plan_id, "cycle": cycle, "sid": str(current[0])},
    )
    db.commit()

    return {
        "subscription_id": str(current[0]),
        "new_plan": new_plan.name,
        "billing_cycle": cycle,
        "status": "updated",
        "mode": "local",
    }


@router.post("/cancel", response_model=dict[str, Any])
def cancel_subscription_admin(tenant_id: str, db: Session = Depends(get_db)):
    tenant_id = _validate_tenant_id(tenant_id)
    set_tenant_guc(db, tenant_id, persist=True)

    current = db.execute(
        text(
            "SELECT id, current_period_end, stripe_subscription_id "
            "FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND status IN ('active', 'trialing', 'past_due') "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).first()
    if not current:
        raise HTTPException(status_code=404, detail="no_active_subscription")

    if current[2] and stripe_is_configured():
        stripe = get_stripe_module()
        updated = stripe.Subscription.modify(
            current[2],
            cancel_at_period_end=True,
        )
        current_period_end = unix_to_dt(updated.get("current_period_end"))
        status = stripe_status_to_local(updated.get("status"))
        db.execute(
            text(
                "UPDATE tenant_subscriptions "
                "SET status = :status, canceled_at = CURRENT_TIMESTAMP, current_period_end = :current_period_end, updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :sid"
            ),
            {
                "sid": str(current[0]),
                "status": status,
                "current_period_end": current_period_end,
            },
        )
        db.commit()
        return {
            "subscription_id": str(current[0]),
            "status": status,
            "access_until": current_period_end.isoformat() if current_period_end else None,
            "mode": "stripe",
            "cancel_at_period_end": True,
        }

    db.execute(
        text(
            "UPDATE tenant_subscriptions SET status = 'canceled', canceled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = :sid"
        ),
        {"sid": str(current[0])},
    )
    db.commit()

    return {
        "subscription_id": str(current[0]),
        "status": "canceled",
        "access_until": current[1].isoformat() if current[1] else None,
        "mode": "local",
    }


@router.post("/portal", response_model=dict[str, Any])
def create_billing_portal_admin(
    tenant_id: str,
    payload: BillingPortalIn,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_id = _validate_tenant_id(tenant_id)
    set_tenant_guc(db, tenant_id, persist=True)
    if not stripe_is_configured():
        raise HTTPException(status_code=503, detail="stripe_not_configured")

    customer_id = load_existing_customer_id(db, tenant_id)
    if not customer_id:
        row = db.execute(
            text(
                "SELECT stripe_subscription_id FROM tenant_subscriptions "
                "WHERE tenant_id = :tid AND stripe_subscription_id IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 1"
            ),
            {"tid": tenant_id},
        ).first()
        if row and row[0]:
            stripe = get_stripe_module()
            subscription = stripe.Subscription.retrieve(row[0])
            customer_id = str(subscription.get("customer") or "")
            if customer_id:
                db.execute(
                    text(
                        "UPDATE tenant_subscriptions SET stripe_customer_id = :customer_id, updated_at = CURRENT_TIMESTAMP "
                        "WHERE tenant_id = :tid"
                    ),
                    {"customer_id": customer_id, "tid": tenant_id},
                )
                db.commit()

    if not customer_id:
        raise HTTPException(status_code=404, detail="stripe_customer_not_found")

    stripe = get_stripe_module()
    return_url = resolve_return_url(
        request, f"/admin/companies/{tenant_id}/config", payload.return_url
    )
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return {"portal_url": session.get("url"), "customer_id": customer_id}
