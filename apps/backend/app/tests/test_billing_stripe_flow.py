from __future__ import annotations

import sys
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import text

from app.modules.billing.interface.http import tenant as tenant_billing


def _ensure_billing_tables(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                price_monthly REAL,
                price_yearly REAL,
                max_users INTEGER,
                max_branches INTEGER,
                included_modules TEXT,
                features TEXT,
                is_active BOOLEAN,
                stripe_price_id_monthly TEXT,
                stripe_price_id_yearly TEXT,
                sort_order INTEGER
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_subscriptions (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                plan_id TEXT NOT NULL,
                status TEXT,
                billing_cycle TEXT,
                current_period_start TEXT,
                current_period_end TEXT,
                stripe_subscription_id TEXT,
                stripe_customer_id TEXT,
                canceled_at TEXT,
                trial_ends_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.commit()


def _seed_plan(db, *, plan_id: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO subscription_plans (
                id, name, display_name, price_monthly, price_yearly,
                max_users, max_branches, included_modules, features, is_active,
                stripe_price_id_monthly, stripe_price_id_yearly, sort_order
            ) VALUES (
                :id, 'pro', 'Pro', 29, 290,
                10, 3, '[\"customers\", \"users\", \"einvoicing\"]', '{}', 1,
                'price_monthly_pro', 'price_yearly_pro', 1
            )
            """
        ),
        {"id": plan_id},
    )
    db.commit()


def _tenant_headers(client, usuario_empresa_factory):
    user, _tenant = usuario_empresa_factory(
        email="billing-admin@example.com",
        username="billingadmin",
        password="tenant123",
    )
    user.is_verified = True
    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": user.email, "password": "tenant123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, _tenant


def _admin_headers(client, superuser_factory):
    password = "secret123"
    superuser_factory(
        email="billing-admin-root@example.com",
        username="billing_root",
        password=password,
    )
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "billing-admin-root@example.com", "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_plan_catalog_lists_available_plans(client, db, superuser_factory):
    _ensure_billing_tables(db)
    plan_id = str(uuid4())
    _seed_plan(db, plan_id=plan_id)
    headers = _admin_headers(client, superuser_factory)

    response = client.get("/api/v1/admin/billing/plans", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == plan_id
    assert body[0]["display_name"] == "Pro"
    assert body[0]["max_users"] == 10
    assert body[0]["included_modules"] == ["customers", "users", "einvoicing"]


def test_tenant_plan_catalog_normalizes_included_modules(client, db, usuario_empresa_factory):
    _ensure_billing_tables(db)
    plan_id = str(uuid4())
    _seed_plan(db, plan_id=plan_id)
    headers, _tenant = _tenant_headers(client, usuario_empresa_factory)

    response = client.get("/api/v1/tenant/billing/plans", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    plan = next(item for item in body if item["id"] == plan_id)
    assert plan["included_modules"] == ["customers", "users", "einvoicing"]


def test_tenant_subscribe_returns_checkout_url(client, db, usuario_empresa_factory, monkeypatch):
    _ensure_billing_tables(db)
    plan_id = str(uuid4())
    _seed_plan(db, plan_id=plan_id)
    headers, _tenant = _tenant_headers(client, usuario_empresa_factory)

    captured: dict[str, object] = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return {"id": "cs_test_123", "url": "https://checkout.example/session"}

    fake_stripe = SimpleNamespace(
        checkout=SimpleNamespace(Session=SimpleNamespace(create=fake_create)),
    )

    monkeypatch.setattr(tenant_billing, "stripe_is_configured", lambda: True)
    monkeypatch.setattr(
        tenant_billing, "ensure_stripe_customer", lambda *args, **kwargs: "cus_test_123"
    )
    monkeypatch.setattr(tenant_billing, "get_stripe_module", lambda: fake_stripe)

    response = client.post(
        "/api/v1/tenant/billing/subscribe",
        headers=headers,
        json={
            "plan_id": plan_id,
            "billing_cycle": "yearly",
            "return_url": "http://localhost:5173/settings/subscription",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["mode"] == "stripe_checkout"
    assert response.json()["checkout_url"] == "https://checkout.example/session"
    assert captured["customer"] == "cus_test_123"
    assert captured["line_items"] == [{"price": "price_yearly_pro", "quantity": 1}]
    assert captured["success_url"] == "http://localhost:5173/settings/subscription"


def test_tenant_billing_portal_returns_portal_url(client, db, usuario_empresa_factory, monkeypatch):
    _ensure_billing_tables(db)
    plan_id = str(uuid4())
    _seed_plan(db, plan_id=plan_id)
    headers, tenant = _tenant_headers(client, usuario_empresa_factory)

    db.execute(
        text(
            """
            INSERT INTO tenant_subscriptions (
                id, tenant_id, plan_id, status, billing_cycle, stripe_customer_id
            ) VALUES (
                :id, :tenant_id, :plan_id, 'active', 'monthly', 'cus_portal_123'
            )
            """
        ),
        {"id": str(uuid4()), "tenant_id": str(tenant.id), "plan_id": plan_id},
    )
    db.commit()

    fake_stripe = SimpleNamespace(
        billing_portal=SimpleNamespace(
            Session=SimpleNamespace(
                create=lambda **kwargs: {"url": "https://billing.example/portal", **kwargs}
            )
        )
    )

    monkeypatch.setattr(tenant_billing, "stripe_is_configured", lambda: True)
    monkeypatch.setattr(tenant_billing, "get_stripe_module", lambda: fake_stripe)

    response = client.post(
        "/api/v1/tenant/billing/portal",
        headers=headers,
        json={"return_url": "http://localhost:5173/settings/subscription"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["portal_url"] == "https://billing.example/portal"
    assert response.json()["customer_id"] == "cus_portal_123"


def test_stripe_webhook_checkout_completed_upserts_subscription(client, db, monkeypatch):
    _ensure_billing_tables(db)
    tenant_id = str(uuid4())
    plan_id = str(uuid4())
    _seed_plan(db, plan_id=plan_id)

    fake_subscription = {
        "id": "sub_test_123",
        "customer": "cus_test_123",
        "status": "active",
        "current_period_start": 1_700_000_000,
        "current_period_end": 1_700_086_400,
        "trial_end": None,
        "items": {"data": [{"price": {"id": "price_monthly_pro"}}]},
    }

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    fake_stripe_module = SimpleNamespace(
        Webhook=SimpleNamespace(
            construct_event=lambda body, sig, secret: {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "id": "cs_test_123",
                        "subscription": "sub_test_123",
                        "client_reference_id": tenant_id,
                        "metadata": {
                            "tenant_id": tenant_id,
                            "plan_id": plan_id,
                            "billing_cycle": "monthly",
                        },
                    }
                },
            }
        )
    )
    monkeypatch.setitem(sys.modules, "stripe", fake_stripe_module)
    monkeypatch.setattr(
        tenant_billing,
        "get_stripe_module",
        lambda: SimpleNamespace(
            Subscription=SimpleNamespace(retrieve=lambda _sid: fake_subscription)
        ),
    )

    response = client.post(
        "/api/v1/tenant/billing/webhook/stripe",
        content=b"{}",
        headers={"stripe-signature": "sig_test"},
    )

    assert response.status_code == 200, response.text
    row = db.execute(
        text(
            "SELECT tenant_id, plan_id, status, billing_cycle, stripe_subscription_id, stripe_customer_id "
            "FROM tenant_subscriptions WHERE stripe_subscription_id = 'sub_test_123'"
        )
    ).first()
    assert row is not None
    assert row[0] == tenant_id
    assert row[1] == plan_id
    assert row[2] == "active"
    assert row[3] == "monthly"
    assert row[4] == "sub_test_123"
    assert row[5] == "cus_test_123"


def test_admin_billing_rejects_tenant_scope_token(client, db, usuario_empresa_factory):
    _ensure_billing_tables(db)
    headers, tenant = _tenant_headers(client, usuario_empresa_factory)

    response = client.get(
        f"/api/v1/admin/companies/{tenant.id}/billing/plans",
        headers=headers,
    )

    assert response.status_code == 403
