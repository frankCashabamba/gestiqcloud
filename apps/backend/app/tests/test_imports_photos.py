from fastapi.testclient import TestClient


def _tenant_token(client: TestClient, usuario_empresa_factory):
    import uuid

    suffix = uuid.uuid4().hex[:6]
    username = f"ph_{suffix}"
    email = f"ph_{suffix}@x.com"
    usuario, empresa = usuario_empresa_factory(email=email, username=username, password="secret")
    r = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": username, "password": "secret"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("access_token") or data.get("token")


def test_upload_photo_creates_item_with_attachment(client: TestClient, db, usuario_empresa_factory, tmp_path, monkeypatch):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Relax limits for this test
    monkeypatch.setenv("IMPORTS_MAX_UPLOAD_MB", "5")

    # Create batch for receipts via OCR
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "receipts", "origin": "ocr"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    batch = r.json()

    # Create tiny JPEG-like bytes
    p = tmp_path / "img.jpg"
    p.write_bytes(b"\xFF\xD8\xFF\xDB" + b"0" * 1024)

    with open(p, "rb") as f:
        r2 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/photos",
            headers=headers,
            files={"file": ("img.jpg", f, "image/jpeg")},
        )
    assert r2.status_code == 200, r2.text
    item = r2.json()
    assert item["id"], "should return created item"
    assert item["status"] in ("OK", "ERROR_VALIDATION")

    # List items in batch and ensure one exists
    rlist = client.get(f"/api/v1/imports/batches/{batch['id']}/items", headers=headers)
    assert rlist.status_code == 200
    items = rlist.json()
    assert len(items) == 1


def test_attach_photo_to_item_revalidates(client: TestClient, db, usuario_empresa_factory, tmp_path, monkeypatch):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    monkeypatch.setenv("IMPORTS_MAX_UPLOAD_MB", "5")

    # Batch
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "receipts", "origin": "ocr"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    # First photo
    p1 = tmp_path / "p1.jpg"
    p1.write_bytes(b"\xFF\xD8\xFF\xDB" + b"a" * 512)
    with open(p1, "rb") as f1:
        r2 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/photos",
            headers=headers,
            files={"file": ("p1.jpg", f1, "image/jpeg")},
        )
    assert r2.status_code == 200
    item = r2.json()
    item_id = item["id"]

    # Attach second photo to same item
    p2 = tmp_path / "p2.jpg"
    p2.write_bytes(b"\xFF\xD8\xFF\xDB" + b"b" * 512)
    with open(p2, "rb") as f2:
        r3 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/items/{item_id}/photos",
            headers=headers,
            files={"file": ("p2.jpg", f2, "image/jpeg")},
        )
    assert r3.status_code == 200, r3.text
    updated = r3.json()
    assert updated["id"] == item_id
    assert updated["status"] in ("OK", "ERROR_VALIDATION")


def test_photo_errors_csv_reflects_validation(client: TestClient, db, usuario_empresa_factory, tmp_path, monkeypatch):
    tok = _tenant_token(client, usuario_empresa_factory)
    headers = {"Authorization": f"Bearer {tok}"}

    # Keep limits generous for this test
    monkeypatch.setenv("IMPORTS_MAX_UPLOAD_MB", "5")

    # Batch for receipts (so expenses validator applies)
    r = client.post(
        "/api/v1/imports/batches",
        json={"source_type": "receipts", "origin": "ocr"},
        headers=headers,
    )
    assert r.status_code == 200
    batch = r.json()

    # Create bytes that will produce empty OCR (stub returns "")
    p = tmp_path / "empty.jpg"
    p.write_bytes(b"\xFF\xD8\xFF\xDB" + b"z" * 256)
    with open(p, "rb") as f:
        r2 = client.post(
            f"/api/v1/imports/batches/{batch['id']}/photos",
            headers=headers,
            files={"file": ("empty.jpg", f, "image/jpeg")},
        )
    assert r2.status_code == 200, r2.text

    # Export errors.csv and verify it contains header and a field name
    rcsv = client.get(f"/api/v1/imports/batches/{batch['id']}/errors.csv", headers=headers)
    assert rcsv.status_code == 200
    assert rcsv.headers.get("content-type", "").startswith("text/csv")
    csv_text = rcsv.text
    assert "idx,campo,error,valor" in csv_text.replace(" ", "")
    # Expect expense_date or amount error entries present due to empty OCR
    assert ("expense_date" in csv_text) or ("amount" in csv_text)
