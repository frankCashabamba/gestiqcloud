import pytest
from fastapi.testclient import TestClient


@pytest.mark.xfail(reason="Admin modulos router not mounted in this minimal test env")
def test_admin_modulos_list(client: TestClient, db, superuser_factory, admin_login):
    tok = admin_login()
    # ping route to assert router is mounted and auth works
    rp = client.get("/api/v1/admin/modules/ping", headers={"Authorization": f"Bearer {tok}"})
    assert rp.status_code == 200
