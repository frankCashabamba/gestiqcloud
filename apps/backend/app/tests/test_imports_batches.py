from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    usuario, tenant = usuario_empresa_factory(email="imp@x.com", username="imp", password="secret")
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "imp", "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_imports_batch_flow_minimal(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # 1) Create batch
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    batch = r.json()

    # 2) Ingest two rows (one invalid)
    rows = [
        {
            "invoice_number": "F-001",
            "invoice_date": "2024-01-02",
            "net_amount": 90.0,
            "tax_amount": 10.0,
            "total_amount": 100.0,
        },
        {
            "invoice_number": "F-002",
            "invoice_date": "2024-01-02",
            "net_amount": 50.0,
            "tax_amount": 5.0,
            "total_amount": 60.0,
        },  # invalid total
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    items = r2.json()
    assert len(items) == 2
    statuses = {it["idx"]: it["status"] for it in items}
    assert statuses[0] == "OK"
    assert statuses[1].startswith("ERROR")

    # 3) Patch invalid item to correct total and revalidate
    # Find item id by fetching list
    r3 = client.get(
        f"/api/v1/imports/batches/{batch['id']}/items",
        headers=headers,
    )
    assert r3.status_code == 200
    listed = r3.json()
    bad = next(x for x in listed if x["idx"] == 1)
    r4 = client.patch(
        f"/api/v1/imports/batches/{batch['id']}/items/{bad['id']}",
        json={"field": "total_amount", "value": 55.0},
        headers=headers,
    )
    assert r4.status_code == 200, r4.text
    patched = r4.json()
    assert patched["status"] in ("OK", "ERROR_VALIDATION")

    # 4) Revalidate batch and expect both OK
    r5 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/validate",
        headers=headers,
    )
    assert r5.status_code == 200
    after = r5.json()
    assert all(it["status"] == "OK" for it in after)

    # 5) Promote and check counts
    r6 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/promote",
        headers=headers,
    )
    assert r6.status_code == 200
    pr = r6.json()
    assert pr["created"] >= 1

    # 6) List with lineage
    r7 = client.get(
        f"/api/v1/imports/batches/{batch['id']}/items",
        params={"with": "lineage"},
        headers=headers,
    )
    assert r7.status_code == 200
    enriched = r7.json()
    assert any((it.get("lineage") or []) for it in enriched)
