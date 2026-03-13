from fastapi.testclient import TestClient


def _admin_headers(client: TestClient, superuser_factory) -> dict[str, str]:
    password = "admin123!"
    user = superuser_factory(username="configadmin", email="configadmin@example.com", password=password)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": user.username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_config_language_crud(client: TestClient, superuser_factory):
    import uuid

    headers = _admin_headers(client, superuser_factory)
    # Use unique code to avoid conflicts (max 10 chars)
    code = f"es_{uuid.uuid4().hex[:5]}"

    # Create language
    payload = {"code": code, "name": "Spanish", "active": True}
    r = client.post("/api/v1/admin/config/language", json=payload, headers=headers)
    assert r.status_code == 200
    language = r.json()
    assert language["code"] == code

    # List languages and ensure it is present
    r2 = client.get("/api/v1/admin/config/language", headers=headers)
    assert r2.status_code == 200
    items = r2.json()
    assert any(it["code"] == code for it in items)


def test_admin_config_business_type_crud(client: TestClient, superuser_factory):
    headers = _admin_headers(client, superuser_factory)
    # Create business type
    payload = {"name": "SRL"}
    r = client.post("/api/v1/admin/config/business-type", json=payload, headers=headers)
    assert r.status_code == 200
    business_type = r.json()
    assert business_type["name"] == "SRL"

    # Update
    r2 = client.put(
        f"/api/v1/admin/config/business-type/{business_type['id']}",
        json={"name": "EIRL"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "EIRL"


def test_admin_config_requires_admin_scope(client: TestClient):
    response = client.get("/api/v1/admin/config/tax-type")
    assert response.status_code == 403
