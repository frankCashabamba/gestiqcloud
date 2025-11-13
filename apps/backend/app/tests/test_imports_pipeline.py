from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    import uuid

    suffix = uuid.uuid4().hex[:6]
    username = f"imp_{suffix}"
    email = f"imp_{suffix}@x.com"
    usuario, tenant = usuario_empresa_factory(
        email=email, username=username, password="secret"
    )
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": username, "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_ingest_idempotency(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create batch (no mapping)
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    batch = r.json()

    rows = [
        {
            "invoice_number": "X-1",
            "invoice_date": "2024-02-01",
            "net_amount": 100,
            "tax_amount": 21,
            "total_amount": 121,
        },
        {
            "invoice_number": "X-2",
            "invoice_date": "2024-02-01",
            "net_amount": 10,
            "tax_amount": 2,
            "total_amount": 12,
        },
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    first = r2.json()
    assert len(first) == 2

    # Re-ingest same rows: idempotency should skip
    r3 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r3.status_code == 200, r3.text
    second = r3.json()
    # Items listed should still be 2 for the batch
    assert len(second) == 2


def test_dedupe_keys_skip_on_promotion(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create a mapping with dedupe_keys for invoices
    mp_payload = {
        "name": "Factura dedupe",
        "source_type": "invoices",
        "version": 1,
        "mappings": {
            "invoice_number": "num",
            "invoice_date": "fecha",
            "total_amount": "total",
        },
        "transforms": {"invoice_date": "date"},
        "defaults": {},
        "dedupe_keys": ["invoice_number", "invoice_date", "total_amount"],
    }
    rmp = client.post("/api/v1/imports/mappings", json=mp_payload, headers=headers)
    assert rmp.status_code == 200, rmp.text
    mp_id = rmp.json()["id"]

    # Create batch
    rb = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api", "mapping_id": mp_id},
        headers=headers,
    )
    assert rb.status_code == 200, rb.text
    batch = rb.json()

    rows = [
        {
            "num": "DUP-1",
            "fecha": "2024-02-01",
            "total": 100,
            "net_amount": 82.64,
            "tax_amount": 17.36,
        },
        {
            "num": "DUP-1",
            "fecha": "01/02/2024",
            "total": 100,
            "net_amount": 80,
            "tax_amount": 20,
        },  # same dedupe
    ]
    ri = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows, "mapping_id": mp_id},
        headers=headers,
    )
    assert ri.status_code == 200, ri.text

    # Validate and promote
    rv = client.post(f"/api/v1/imports/batches/{batch['id']}/validate", headers=headers)
    assert rv.status_code == 200
    rp = client.post(f"/api/v1/imports/batches/{batch['id']}/promote", headers=headers)
    assert rp.status_code == 200, rp.text
    promo = rp.json()
    # Expect one created and one skipped due to dedupe hash match
    assert promo["created"] == 1
    assert promo["skipped"] >= 1


def test_patch_and_revalidate(client: TestClient, db, usuario_empresa_factory):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Create batch
    rb = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert rb.status_code == 200
    batch = rb.json()

    # Ingest one invalid invoice (total mismatch)
    rows = [
        {
            "invoice_number": "X-9",
            "invoice_date": "2024-02-01",
            "net_amount": 10,
            "tax_amount": 2,
            "total_amount": 20,
        }
    ]
    ri = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert ri.status_code == 200
    items = ri.json()
    item_id = items[0]["id"]
    assert items[0]["status"] == "ERROR_VALIDATION"

    # Patch the field to fix
    rpatch = client.patch(
        f"/api/v1/imports/batches/{batch['id']}/items/{item_id}",
        json={"field": "total_amount", "value": 12},
        headers=headers,
    )
    assert rpatch.status_code == 200, rpatch.text
    patched = rpatch.json()
    assert patched["status"] == "OK"
    # last_correction should appear when listing with lineage
    rlist = client.get(
        f"/api/v1/imports/batches/{batch['id']}/items?with=lineage",
        headers=headers,
    )
    assert rlist.status_code == 200
    listed = rlist.json()
    found = [x for x in listed if x["id"] == item_id][0]
    assert found.get("last_correction", {}).get("field") == "total_amount"


def test_tenant_scoping_forbids_cross_access(
    client: TestClient, db, usuario_empresa_factory
):
    # Create tenant A and batch
    tok_a = _tenant_token(client, usuario_empresa_factory)
    headers_a = {"Authorization": f"Bearer {tok_a}"}
    rb = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "receipts", "origin": "api"},
        headers=headers_a,
    )
    assert rb.status_code == 200
    batch = rb.json()

    # Create tenant B and try to access tenant A batch
    tok_b = _tenant_token(client, usuario_empresa_factory)
    headers_b = {"Authorization": f"Bearer {tok_b}"}
    rget = client.get(f"/api/v1/imports/batches/{batch['id']}", headers=headers_b)
    assert rget.status_code in (403, 404)
