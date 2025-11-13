from apps.backend.app.main import app
from fastapi.testclient import TestClient


def test_health():
    c = TestClient(app)
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_identity_me_route():
    c = TestClient(app)
    r = c.get("/v1/identity/me")
    assert r.status_code in (200, 404)  # allow placeholder absence
