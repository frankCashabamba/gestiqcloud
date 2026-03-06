from fastapi.testclient import TestClient


def test_list_routes(client: TestClient):
    # Print mounted routes to diagnose missing importador router
    paths = sorted([getattr(r, "path", "") for r in client.app.router.routes])
    # Emit to stdout for visibility in -s runs
    print("ROUTES:", paths)
    # The current import flow is mounted under /api/v1/importador
    assert any(p.startswith("/api/v1/importador") for p in paths), "importador routes not mounted"
