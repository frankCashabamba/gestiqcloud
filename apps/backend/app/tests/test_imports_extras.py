from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    username = f"imp2_{suffix}"
    email = f"imp2_{suffix}@x.com"
    usuario, empresa = usuario_empresa_factory(email=email, username=username, password="secret")
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": username, "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_errors_csv_endpoint(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create batch and ingest one invalid invoice
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    rows = [
        {"invoice_number": "X-1", "invoice_date": "2024-02-01", "net_amount": 100, "tax_amount": 21, "total_amount": 121},
        {"invoice_number": "X-2", "invoice_date": "01/02/2024", "net_amount": 10, "tax_amount": 2, "total_amount": 20},  # invalid
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 200

    # Download errors.csv
    r3 = client.get(f"/api/v1/imports/batches/{batch['id']}/errors.csv", headers=headers)
    assert r3.status_code == 200
    assert r3.headers.get("content-type", "").startswith("text/csv")
    csv_text = r3.text
    # Header present
    assert "idx,campo,error,valor" in csv_text.replace(" ", "")
    # Expect an error line with total_amount
    assert "total_amount" in csv_text


def test_import_mapping_crud(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    payload = {
        "name": "Factura básica",
        "source_type": "invoices",
        "version": 1,
        "mappings": {"invoice_number": "num", "invoice_date": "fecha"},
        "transforms": {"invoice_date": "date"},
        "defaults": {"currency": "EUR"},
        "dedupe_keys": ["issuer_tax_id", "invoice_number", "invoice_date", "total_amount"],
    }
    # Create
    r = client.post("/api/v1/imports/mappings", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    mp = r.json()
    mp_id = mp["id"]

    # List
    r2 = client.get("/api/v1/imports/mappings?source_type=invoices", headers=headers)
    assert r2.status_code == 200
    assert any(x["id"] == mp_id for x in r2.json())

    # Get
    r3 = client.get(f"/api/v1/imports/mappings/{mp_id}", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["name"] == payload["name"]

    # Update
    r4 = client.put(
        f"/api/v1/imports/mappings/{mp_id}",
        json={"name": "Factura v2", "version": 2},
        headers=headers,
    )
    assert r4.status_code == 200
    assert r4.json()["name"] == "Factura v2"
    assert r4.json()["version"] == 2

    # Clone
    r5 = client.post(f"/api/v1/imports/mappings/{mp_id}/clone", headers=headers)
    assert r5.status_code == 200
    clone = r5.json()
    assert clone["name"].startswith("Factura v2") or "copia" in clone["name"].lower()

    # Delete original
    r6 = client.delete(f"/api/v1/imports/mappings/{mp_id}", headers=headers)
    assert r6.status_code == 200
