from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core.dependencies import get_tenant_uuid
from app.modules.reconciliation.interface.http.payments import _resolve_webhook_tenant_id


def test_resolve_webhook_tenant_id_uses_payload_metadata(db):
    tenant_id = uuid4()
    invoice_id = uuid4()
    payload = {
        "eventType": "payment.success",
        "transaction": {
            "metadata": {
                "tenant_id": str(tenant_id),
                "invoice_id": str(invoice_id),
            }
        },
    }

    resolved = _resolve_webhook_tenant_id("kushki", json.dumps(payload).encode("utf-8"), db)
    assert resolved == str(tenant_id)


def test_resolve_webhook_tenant_id_falls_back_to_payment_link_lookup(db):
    tenant_id = uuid4()
    invoice_id = uuid4()

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS payment_links (
                id TEXT PRIMARY KEY,
                tenant_id TEXT,
                invoice_id TEXT,
                session_id TEXT,
                created_at TEXT
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO payment_links (id, tenant_id, invoice_id, session_id, created_at)
            VALUES (:id, :tenant_id, :invoice_id, :session_id, CURRENT_TIMESTAMP)
            """
        ),
        {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "invoice_id": str(invoice_id),
            "session_id": "stripe-session-1",
        },
    )
    db.commit()

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "stripe-session-1",
                "metadata": {
                    "invoice_id": str(invoice_id),
                },
                "payment_intent": "pi_123",
            }
        },
    }

    resolved = _resolve_webhook_tenant_id("stripe", json.dumps(payload).encode("utf-8"), db)
    assert resolved == str(tenant_id)


def test_sales_tenant_uuid_rejects_malformed_claim():
    request = SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": "bad-tenant"}))

    with pytest.raises(HTTPException) as exc:
        get_tenant_uuid(request)

    assert exc.value.status_code == 401
