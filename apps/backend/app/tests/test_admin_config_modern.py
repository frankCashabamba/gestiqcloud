from fastapi.testclient import TestClient


def test_admin_config_language_crud(client: TestClient):
    import uuid

    # Use unique code to avoid conflicts (max 10 chars)
    code = f"es_{uuid.uuid4().hex[:5]}"

    # Create language
    payload = {"code": code, "name": "Spanish", "active": True}
    r = client.post("/api/v1/admin/config/language", json=payload)
    assert r.status_code == 200
    language = r.json()
    assert language["code"] == code

    # List languages and ensure it is present
    r2 = client.get("/api/v1/admin/config/language")
    assert r2.status_code == 200
    items = r2.json()
    assert any(it["code"] == code for it in items)


def test_admin_config_business_type_crud(client: TestClient):
    # Create business type
    payload = {"name": "SRL"}
    r = client.post("/api/v1/admin/config/business-type", json=payload)
    assert r.status_code == 200
    business_type = r.json()
    assert business_type["name"] == "SRL"

    # Update
    r2 = client.put(
        f"/api/v1/admin/config/business-type/{business_type['id']}", json={"name": "EIRL"}
    )
    assert r2.status_code == 200
    assert r2.json()["name"] == "EIRL"
