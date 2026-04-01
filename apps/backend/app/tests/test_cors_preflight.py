from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import allow_headers, allow_methods


def test_preflight_allows_tenant_slug_header():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://www.gestiqcloud.com"],
        allow_credentials=True,
        allow_methods=allow_methods,
        allow_headers=allow_headers,
        max_age=86400,
    )

    @app.get("/api/v1/company/settings/theme")
    async def theme():
        return {"ok": True}

    client = TestClient(app)
    response = client.options(
        "/api/v1/company/settings/theme",
        headers={
            "Origin": "https://www.gestiqcloud.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": (
                "authorization,content-type,x-client-version,"
                "x-client-revision,x-csrf-token,x-tenant-slug"
            ),
        },
    )

    assert response.status_code == 200
    allow_headers_value = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-tenant-slug" in allow_headers_value
    assert response.headers.get("access-control-allow-origin") == "https://www.gestiqcloud.com"
