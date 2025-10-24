from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    usuario, empresa = usuario_empresa_factory(email="dup@x.com", username="dup", password="secret")
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "dup", "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_promote_skips_duplicates(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create batch and ingest two identical OK invoices
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    rows = [
        {"invoice_number": "DUP-1", "invoice_date": "2024-01-02", "net_amount": 90.0, "tax_amount": 10.0, "total_amount": 100.0},
        {"invoice_number": "DUP-1", "invoice_date": "2024-01-02", "net_amount": 90.0, "tax_amount": 10.0, "total_amount": 100.0},
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 200

    # Promote first time
    r3 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/promote",
        headers=headers,
    )
    assert r3.status_code == 200
    first = r3.json()
    assert first["created"] >= 1

    # Promote again should skip duplicates
    r4 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/promote",
        headers=headers,
    )
    assert r4.status_code == 200
    second = r4.json()
    assert second["skipped"] >= first["created"]

