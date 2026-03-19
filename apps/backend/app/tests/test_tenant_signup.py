from sqlalchemy import text


def test_tenant_signup_creates_company_and_allows_login(client, db):
    response = client.post(
        "/api/v1/tenant/auth/signup",
        json={
            "company_name": "Signup Demo SL",
            "first_name": "Frank",
            "last_name": "Tester",
            "email": "signup-demo@example.com",
            "password": "StrongPass1!",
            "country_code": "ES",
            "default_language": "es",
            "timezone": "Europe/Madrid",
            "currency": "EUR",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ok"] is True
    assert payload["requires_onboarding"] is True
    assert payload["tenant_slug"]

    row = db.execute(
        text(
            "SELECT name, slug, country_code, base_currency " "FROM tenants WHERE id = :tenant_id"
        ),
        {"tenant_id": payload["tenant_id"]},
    ).first()
    assert row is not None
    assert row[0] == "Signup Demo SL"
    assert row[2] == "ES"
    assert row[3] == "EUR"

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={
            "identificador": "signup-demo@example.com",
            "password": "StrongPass1!",
        },
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]
