from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass
class BillingPlanRecord:
    id: str
    name: str
    display_name: str | None
    price_monthly: float
    price_yearly: float | None
    stripe_price_id_monthly: str | None
    stripe_price_id_yearly: str | None


def stripe_is_configured() -> bool:
    return bool((os.getenv("STRIPE_SECRET_KEY") or "").strip())


def get_stripe_module():
    secret_key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not secret_key:
        raise HTTPException(status_code=503, detail="stripe_not_configured")

    import stripe

    stripe.api_key = secret_key
    return stripe


def load_plan(db: Session, plan_id: str) -> BillingPlanRecord | None:
    row = db.execute(
        text(
            "SELECT id, name, display_name, price_monthly, price_yearly, "
            "stripe_price_id_monthly, stripe_price_id_yearly "
            "FROM subscription_plans WHERE id = :pid AND is_active = true"
        ),
        {"pid": plan_id},
    ).first()
    if not row:
        return None
    return BillingPlanRecord(
        id=str(row[0]),
        name=row[1],
        display_name=row[2],
        price_monthly=float(row[3] or 0),
        price_yearly=float(row[4]) if row[4] else None,
        stripe_price_id_monthly=row[5],
        stripe_price_id_yearly=row[6],
    )


def get_price_id_for_cycle(plan: BillingPlanRecord, billing_cycle: str) -> str | None:
    if billing_cycle == "yearly":
        return plan.stripe_price_id_yearly or plan.stripe_price_id_monthly
    return plan.stripe_price_id_monthly


def resolve_return_url(request: Request, fallback_path: str, return_url: str | None = None) -> str:
    candidate = (return_url or "").strip()
    if candidate:
        parsed = urlparse(candidate)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return candidate

    referer = (request.headers.get("referer") or "").strip()
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return referer

    origin = (request.headers.get("origin") or os.getenv("FRONTEND_URL") or "").strip()
    if origin:
        parsed = urlparse(origin)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return f"{origin.rstrip('/')}{fallback_path}"

    return f"{str(request.base_url).rstrip('/')}{fallback_path}"


def load_billing_contact(db: Session, tenant_id: str) -> tuple[str | None, str | None]:
    row = db.execute(
        text(
            "SELECT t.name, cu.email "
            "FROM tenants t "
            "LEFT JOIN company_users cu "
            "  ON cu.tenant_id = t.id AND coalesce(cu.is_company_admin, false) = true "
            "WHERE t.id = :tid "
            "ORDER BY cu.id ASC "
            "LIMIT 1"
        ),
        {"tid": tenant_id},
    ).first()
    if not row:
        return None, None
    return row[1], row[0]


def load_existing_customer_id(db: Session, tenant_id: str) -> str | None:
    row = db.execute(
        text(
            "SELECT stripe_customer_id "
            "FROM tenant_subscriptions "
            "WHERE tenant_id = :tid AND stripe_customer_id IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).first()
    return str(row[0]) if row and row[0] else None


def ensure_stripe_customer(db: Session, tenant_id: str, email: str | None, name: str | None) -> str:
    existing = load_existing_customer_id(db, tenant_id)
    if existing:
        return existing

    stripe = get_stripe_module()
    customer = stripe.Customer.create(
        email=email or None,
        name=name or None,
        metadata={"tenant_id": tenant_id},
    )
    return str(customer["id"])


def stripe_status_to_local(status: str | None) -> str:
    status_map = {
        "active": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "trialing": "trialing",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
    }
    return status_map.get(status or "", status or "active")


def unix_to_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except Exception:
        return None


def sync_subscription_from_stripe(
    db: Session,
    *,
    tenant_id: str,
    plan_id: str,
    billing_cycle: str,
    stripe_subscription: dict[str, Any],
) -> dict[str, Any]:
    stripe_subscription_id = str(stripe_subscription.get("id") or "")
    stripe_customer_id = str(stripe_subscription.get("customer") or "")
    status = stripe_status_to_local(stripe_subscription.get("status"))
    current_period_start = unix_to_dt(stripe_subscription.get("current_period_start"))
    current_period_end = unix_to_dt(stripe_subscription.get("current_period_end"))
    trial_ends_at = unix_to_dt(stripe_subscription.get("trial_end"))

    existing = db.execute(
        text(
            "SELECT id "
            "FROM tenant_subscriptions "
            "WHERE stripe_subscription_id = :stripe_subscription_id "
            "   OR (tenant_id = :tenant_id AND status IN ('active', 'trialing', 'past_due', 'pending')) "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {
            "stripe_subscription_id": stripe_subscription_id,
            "tenant_id": tenant_id,
        },
    ).first()

    if existing:
        db.execute(
            text(
                "UPDATE tenant_subscriptions "
                "SET plan_id = :plan_id, billing_cycle = :billing_cycle, status = :status, "
                "    current_period_start = :current_period_start, "
                "    current_period_end = :current_period_end, "
                "    trial_ends_at = :trial_ends_at, "
                "    stripe_subscription_id = :stripe_subscription_id, "
                "    stripe_customer_id = :stripe_customer_id, "
                "    updated_at = CURRENT_TIMESTAMP "
                "WHERE id = :subscription_id"
            ),
            {
                "subscription_id": str(existing[0]),
                "plan_id": plan_id,
                "billing_cycle": billing_cycle,
                "status": status,
                "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "trial_ends_at": trial_ends_at,
                "stripe_subscription_id": stripe_subscription_id or None,
                "stripe_customer_id": stripe_customer_id or None,
            },
        )
    else:
        row = db.execute(
            text(
                "INSERT INTO tenant_subscriptions("
                "tenant_id, plan_id, status, billing_cycle, current_period_start, current_period_end, "
                "trial_ends_at, stripe_subscription_id, stripe_customer_id"
                ") VALUES ("
                ":tenant_id, :plan_id, :status, :billing_cycle, :current_period_start, :current_period_end, "
                ":trial_ends_at, :stripe_subscription_id, :stripe_customer_id"
                ") RETURNING id"
            ),
            {
                "tenant_id": tenant_id,
                "plan_id": plan_id,
                "status": status,
                "billing_cycle": billing_cycle,
                "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "trial_ends_at": trial_ends_at,
                "stripe_subscription_id": stripe_subscription_id or None,
                "stripe_customer_id": stripe_customer_id or None,
            },
        ).first()
        existing = row

    db.commit()
    return {
        "subscription_id": str(existing[0]),
        "status": status,
        "billing_cycle": billing_cycle,
        "current_period_end": current_period_end.isoformat() if current_period_end else None,
        "stripe_subscription_id": stripe_subscription_id or None,
        "stripe_customer_id": stripe_customer_id or None,
    }


def find_plan_by_stripe_price(db: Session, price_id: str | None) -> tuple[str | None, str | None]:
    if not price_id:
        return None, None
    row = db.execute(
        text(
            "SELECT id, "
            "CASE WHEN stripe_price_id_yearly = :price_id THEN 'yearly' ELSE 'monthly' END AS billing_cycle "
            "FROM subscription_plans "
            "WHERE stripe_price_id_monthly = :price_id OR stripe_price_id_yearly = :price_id "
            "LIMIT 1"
        ),
        {"price_id": price_id},
    ).first()
    if not row:
        return None, None
    return str(row[0]), row[1]
