from fastapi.testclient import TestClient

from app.models.core.module import Module


def _admin_token(client: TestClient, superuser_factory) -> str:
    superuser_factory(email="root@admin.com", username="root", password="secret")
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "root", "password": "secret"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_register_modules_falls_back_to_backend_catalog(client: TestClient, db, superuser_factory):
    token = _admin_token(client, superuser_factory)
    response = client.post(
        "/api/v1/admin/modules/register-modules",
        json={"dir": "Z:/missing/modules"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["source"] == "backend_catalog"
    assert "registrados" not in data
    assert "ya_existentes" not in data
    assert "ignorados" not in data
    assert "warnings" in data
    assert "inventory" in (data["registered"] + data["already_existing"])

    inventory = db.query(Module).filter(Module.name == "inventory").first()
    assert inventory is not None
    assert inventory.initial_template == "inventory"


def test_register_modules_does_not_duplicate_catalog_entries(
    client: TestClient, db, superuser_factory
):
    token = _admin_token(client, superuser_factory)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"dir": "Z:/missing/modules"}

    first = client.post("/api/v1/admin/modules/register-modules", json=payload, headers=headers)
    assert first.status_code == 200, first.text

    second = client.post("/api/v1/admin/modules/register-modules", json=payload, headers=headers)
    assert second.status_code == 200, second.text
    data = second.json()

    assert data["registered"] == []
    assert "inventory" in data["already_existing"]
    assert db.query(Module).filter(Module.name == "inventory").count() == 1
