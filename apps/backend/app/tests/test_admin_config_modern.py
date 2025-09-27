from fastapi.testclient import TestClient


def test_admin_config_idioma_crud(client: TestClient):
    # Create idioma
    payload = {"codigo": "es", "nombre": "Español", "activo": True}
    r = client.post("/api/v1/admin/config/idioma", json=payload)
    assert r.status_code == 200
    idioma = r.json()
    assert idioma["codigo"] == "es"

    # List idiomas and ensure it is present
    r2 = client.get("/api/v1/admin/config/idioma")
    assert r2.status_code == 200
    items = r2.json()
    assert any(it["codigo"] == "es" for it in items)


def test_admin_config_tipo_empresa_crud(client: TestClient):
    # Create tipo empresa
    payload = {"nombre": "SRL"}
    r = client.post("/api/v1/admin/config/tipo-empresa", json=payload)
    assert r.status_code == 200
    te = r.json()
    assert te["nombre"] == "SRL"

    # Update
    r2 = client.put(f"/api/v1/admin/config/tipo-empresa/{te['id']}", json={"nombre": "EIRL"})
    assert r2.status_code == 200
    assert r2.json()["nombre"] == "EIRL"
