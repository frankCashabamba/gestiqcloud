from fastapi.testclient import TestClient


def test_list_routes(client: TestClient):
    # Print mounted routes to diagnose missing imports router
    paths = sorted([getattr(r, "path", "") for r in client.app.router.routes])
    # Emit to stdout for visibility in -s runs
    print("ROUTES:", paths)
    # At least base imports prefix should exist when enabled or in sqlite auto-enable
    assert any(p.startswith("/api/v1/imports") for p in paths), "imports routes not mounted"

