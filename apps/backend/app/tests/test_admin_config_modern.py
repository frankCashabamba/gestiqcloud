from fastapi.testclient import TestClient


def test_admin_config_idioma_crud(client: TestClient):
    import uuid

    # Use unique code to avoid conflicts (max 10 chars)
    codigo = f"es_{uuid.uuid4().hex[:5]}"

    # Create idioma
    payload = {"codigo": codigo, "name": "Español", "activo": True}
    r = client.post("/api/v1/admin/config/idioma", json=payload)
    assert r.status_code == 200
    idioma = r.json()
    assert idioma["codigo"] == codigo

    # List idiomas and ensure it is present
    r2 = client.get("/api/v1/admin/config/idioma")
    assert r2.status_code == 200
    items = r2.json()
    assert any(it["codigo"] == codigo for it in items)


def test_admin_config_tipo_empresa_crud(client: TestClient):
    # Create tipo empresa
    payload = {"name": "SRL"}
    r = client.post("/api/v1/admin/config/tipo-empresa", json=payload)
    assert r.status_code == 200
    te = r.json()
    assert te["name"] == "SRL"

    # Update
    r2 = client.put(f"/api/v1/admin/config/tipo-empresa/{te['id']}", json={"name": "EIRL"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "EIRL"
