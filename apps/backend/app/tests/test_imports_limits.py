import os
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.skip(reason="Auth middleware incompatible with test environment")
def test_ingest_limit_413(client: TestClient, db, auth_headers, monkeypatch):
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)

    # Limit to 1 item per ingest
    monkeypatch.setenv("IMPORTS_MAX_ITEMS_PER_BATCH", "1")

    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    rows = [
        {"invoice_number": "A", "invoice_date": "2024-01-01", "net_amount": 1, "tax_amount": 0, "total_amount": 1},
        {"invoice_number": "B", "invoice_date": "2024-01-02", "net_amount": 1, "tax_amount": 0, "total_amount": 1},
    ]
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 413


@pytest.mark.skip(reason="Auth middleware incompatible with test environment")
def test_photo_limits_and_mimetype(client: TestClient, db, auth_headers, monkeypatch, tmp_path):
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)

    # Very small limit to trigger 413
    monkeypatch.setenv("IMPORTS_MAX_UPLOAD_MB", "0.00001")

    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "receipts", "origin": "ocr"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    # Create a small dummy file > limit
    p = tmp_path / "x.bin"
    p.write_bytes(b"x" * 1000)

    with open(p, "rb") as f:
        r2 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/photos",
            headers=headers,
            files={"file": ("x.jpg", f, "image/jpeg")},
        )
    assert r2.status_code == 413

    # Raise limit and send unsupported mimetype -> 422
    monkeypatch.setenv("IMPORTS_MAX_UPLOAD_MB", "10")
    with open(p, "rb") as f:
        r3 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/photos",
            headers=headers,
            files={"file": ("x.txt", f, "text/plain")},
        )
    assert r3.status_code == 422


@pytest.mark.skip(reason="Auth middleware incompatible with test environment")
def test_ingest_throttling_429(client: TestClient, db, auth_headers, monkeypatch):
    tenant_id = str(uuid4())
    headers = auth_headers(tenant_id=tenant_id)

    # Allow only 1 ingest per minute to trigger 429 on the second call
    monkeypatch.setenv("IMPORTS_MAX_INGESTS_PER_MIN", "1")

    # Create batch
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "invoices", "origin": "api"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    rows = [{"invoice_number": "T1", "invoice_date": "2024-01-01", "net_amount": 1, "tax_amount": 0, "total_amount": 1}]
    r1 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r1.status_code == 200
    # Immediate second attempt should be throttled
    r2 = client.post(
        f"/api/v1/imports/batches/{batch['id']}/ingest",
        json={"rows": rows},
        headers=headers,
    )
    assert r2.status_code == 429
