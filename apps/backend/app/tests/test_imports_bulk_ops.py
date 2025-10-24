from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    import uuid
    suffix = uuid.uuid4().hex[:6]
    username = f"bulk_{suffix}"
    email = f"bulk_{suffix}@x.com"
    usuario, empresa = usuario_empresa_factory(email=email, username=username, password="secret")
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": username, "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_bulk_patch_and_reprocess_flow(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create batch and ingest 3 rows (2 invalid totals)
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    rows = [
        {"invoice_number": "B1", "invoice_date": "2024-02-01", "net_amount": 90, "tax_amount": 10, "total_amount": 100},
        {"invoice_number": "B2", "invoice_date": "2024-02-01", "net_amount": 50, "tax_amount": 5, "total_amount": 60},  # bad
        {"invoice_number": "B3", "invoice_date": "01/02/2024", "net_amount": 10, "tax_amount": 2, "total_amount": 13},   # bad
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 200
    items = r2.json()
    assert len(items) == 3

    # List and pick invalid ids
    r3 = client.get(
        f"/api/v1/imports/batches/{batch['id']}/items",
        headers=headers,
    )
    assert r3.status_code == 200
    listed = r3.json()
    invalid = [x for x in listed if x["status"] != "OK"]
    ids = [x["id"] for x in invalid]

    # Bulk patch to fix totals
    r4 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/items/bulk-patch",
        json={"ids": ids, "changes": {"total_amount": None}},  # set None to recompute? We'll set correct totals directly next line
        headers=headers,
    )
    assert r4.status_code == 200

    # Patch precise values
    fixes = {"B2": 55.0, "B3": 12.0}
    for it in listed:
        if it["invoice_number"] if False else None:
            pass
    # Use single PATCH endpoint per item as well (defensive)
    for it in listed:
        if it["idx"] == 1:
            client.patch(
                f"/api/v1/imports/batches/{batch['id']}/items/{it['id']}",
                json={"field": "total_amount", "value": 55.0},
                headers=headers,
            )
        if it["idx"] == 2:
            client.patch(
                f"/api/v1/imports/batches/{batch['id']}/items/{it['id']}",
                json={"field": "total_amount", "value": 12.0},
                headers=headers,
            )

    # Reprocess (revalidate and promote)
    r5 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/reprocess",
        headers=headers,
        params={"scope": "all", "promote": True},
    )
    assert r5.status_code == 200

