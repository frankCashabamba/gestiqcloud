import secrets
from datetime import date

from fastapi.testclient import TestClient

from app.models.expenses.expense import Expense


def test_expenses_list_is_scoped_to_authenticated_tenant(client: TestClient, db, usuario_empresa_factory):
    password_a = secrets.token_urlsafe(12)
    password_b = secrets.token_urlsafe(12)

    user_a, tenant_a = usuario_empresa_factory(
        empresa_nombre="Demo Kusi",
        empresa_slug="demo-kusi",
        username="demo_kusi_owner",
        email="demo-kusi@example.com",
        password=password_a,
    )
    user_b, tenant_b = usuario_empresa_factory(
        empresa_nombre="Otra Empresa",
        empresa_slug="otra-empresa",
        username="other_owner",
        email="other@example.com",
        password=password_b,
    )

    db.add_all(
        [
            Expense(
                tenant_id=tenant_a.id,
                user_id=user_a.id,
                date=date(2026, 3, 9),
                concept="Solo demo-kusi",
                category="manual",
                amount=11.50,
                vat=0,
                total=11.50,
                status="paid",
            ),
            Expense(
                tenant_id=tenant_b.id,
                user_id=user_b.id,
                date=date(2016, 1, 15),
                concept="No debe aparecer",
                category="manual",
                amount=2145.00,
                vat=0,
                total=2145.00,
                status="paid",
            ),
        ]
    )
    db.commit()

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "demo_kusi_owner", "password": password_a},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/tenant/expenses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["concept"] == "Solo demo-kusi"


def test_expense_detail_is_scoped_to_authenticated_tenant(client: TestClient, db, usuario_empresa_factory):
    password_a = secrets.token_urlsafe(12)
    password_b = secrets.token_urlsafe(12)

    user_a, tenant_a = usuario_empresa_factory(
        empresa_nombre="Demo Kusi",
        empresa_slug="demo-kusi",
        username="demo_kusi_reader",
        email="demo-kusi-reader@example.com",
        password=password_a,
    )
    user_b, tenant_b = usuario_empresa_factory(
        empresa_nombre="Otra Empresa",
        empresa_slug="otra-empresa",
        username="other_reader",
        email="other-reader@example.com",
        password=password_b,
    )

    own_expense = Expense(
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        date=date(2026, 3, 9),
        concept="Propio",
        category="manual",
        amount=15.00,
        vat=0,
        total=15.00,
        status="paid",
    )
    foreign_expense = Expense(
        tenant_id=tenant_b.id,
        user_id=user_b.id,
        date=date(2026, 1, 16),
        concept="Ajeno",
        category="manual",
        amount=99.00,
        vat=0,
        total=99.00,
        status="paid",
    )
    db.add_all([own_expense, foreign_expense])
    db.commit()
    db.refresh(foreign_expense)

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "demo_kusi_reader", "password": password_a},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    response = client.get(
        f"/api/v1/tenant/expenses/{foreign_expense.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
