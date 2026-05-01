"""HTTP CRUD tests for /api/v1/tenant/quotes."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.quotes import Quote
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.models.tenant import Tenant


BASE = "/api/v1/tenant/quotes"


def _token_for_tenant(tenant_id: Any, *, is_company_admin: bool = True) -> str:
    from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

    return PyJWTTokenService().issue_access(
        {
            "user_id": str(uuid.uuid4()),
            "tenant_id": str(tenant_id),
            "scope": "tenant",
            "kind": "tenant",
            "is_company_admin": is_company_admin,
            "permisos": {"quotes.manage": True} if not is_company_admin else {},
        }
    )


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant_q(db: Session):
    bind = db.get_bind()
    Tenant.__table__.create(bind=bind, checkfirst=True)
    Quote.__table__.create(bind=bind, checkfirst=True)
    SalesOrder.__table__.create(bind=bind, checkfirst=True)
    SalesOrderItem.__table__.create(bind=bind, checkfirst=True)
    tid = uuid.uuid4()
    db.add(Tenant(id=tid, name=f"Q-{tid.hex[:4]}", slug=f"q-{tid.hex[:8]}", base_currency="EUR"))
    db.commit()
    return {"tenant_id": tid}


def _payload() -> dict:
    return {
        "currency": "EUR",
        "notes": "Presupuesto de prueba",
        "lines": [
            {
                "name": "Servicio A",
                "qty": 2,
                "unit_price": 50.0,
                "tax_rate": 21,
                "discount_percent": 0,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_list_quotes_requires_auth(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_DISABLE_AUTH_BYPASS", "1")
    r = client.get(BASE)
    assert r.status_code in (401, 403)


def test_list_quotes_requires_permission(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"], is_company_admin=False)
    # Without "quotes.manage" permission and without admin → forbidden
    from app.modules.identity.infrastructure.jwt_tokens import PyJWTTokenService

    tok_no_perm = PyJWTTokenService().issue_access(
        {
            "user_id": str(uuid.uuid4()),
            "tenant_id": str(tenant_q["tenant_id"]),
            "scope": "tenant",
            "kind": "tenant",
            "is_company_admin": False,
            "permisos": {},
        }
    )
    r = client.get(BASE, headers=_auth(tok_no_perm))
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_and_get_quote(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    r = client.post(BASE, json=_payload(), headers=_auth(tok))
    assert r.status_code == 201, r.text
    body = r.json()
    qid = body["id"]
    assert body["status"] == "DRAFT"
    assert body["currency"] == "EUR"
    assert body["total"] == pytest.approx(121.0)

    r2 = client.get(f"{BASE}/{qid}", headers=_auth(tok))
    assert r2.status_code == 200
    assert r2.json()["id"] == qid


def test_create_rejects_empty_lines(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    payload = _payload()
    payload["lines"] = []
    r = client.post(BASE, json=payload, headers=_auth(tok))
    assert r.status_code == 400


def test_list_quotes_filter_status(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    client.post(BASE, json=_payload(), headers=_auth(tok))
    r = client.get(f"{BASE}?status=DRAFT", headers=_auth(tok))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert all(row["status"] == "DRAFT" for row in rows)


def test_update_only_drafts(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    qid = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]

    r = client.put(
        f"{BASE}/{qid}", json={"notes": "actualizado"}, headers=_auth(tok)
    )
    assert r.status_code == 200
    assert r.json()["notes"] == "actualizado"

    # Approve, then try to update → 409
    client.post(f"{BASE}/{qid}/approve", headers=_auth(tok))
    r2 = client.put(
        f"{BASE}/{qid}", json={"notes": "no permitido"}, headers=_auth(tok)
    )
    assert r2.status_code == 409


def test_approve_quote(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    qid = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]
    r = client.post(f"{BASE}/{qid}/approve", headers=_auth(tok))
    assert r.status_code == 200
    assert r.json()["status"] == "APPROVED"


def test_convert_quote_creates_sales_order(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    qid = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]
    client.post(f"{BASE}/{qid}/approve", headers=_auth(tok))

    r = client.post(f"{BASE}/{qid}/convert", headers=_auth(tok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["quote_id"] == qid
    assert body["sales_order_id"]

    detail = client.get(f"{BASE}/{qid}", headers=_auth(tok)).json()
    assert detail["status"] == "CONVERTED"
    assert detail["converted_to_order_id"] == body["sales_order_id"]


def test_convert_rejects_non_approved(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    qid = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]
    r = client.post(f"{BASE}/{qid}/convert", headers=_auth(tok))
    assert r.status_code == 400


def test_delete_only_drafts(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    qid = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]

    r = client.delete(f"{BASE}/{qid}", headers=_auth(tok))
    assert r.status_code == 204

    # Recreate + approve → cannot delete
    qid2 = client.post(BASE, json=_payload(), headers=_auth(tok)).json()["id"]
    client.post(f"{BASE}/{qid2}/approve", headers=_auth(tok))
    r2 = client.delete(f"{BASE}/{qid2}", headers=_auth(tok))
    assert r2.status_code == 409


def test_get_quote_404(client: TestClient, tenant_q) -> None:
    tok = _token_for_tenant(tenant_q["tenant_id"])
    r = client.get(f"{BASE}/{uuid.uuid4()}", headers=_auth(tok))
    assert r.status_code == 404
