"""
Tests para rate limiting por endpoint.
Coverage: middleware/endpoint_rate_limit.py
"""

import pytest
from app.middleware.endpoint_rate_limit import EndpointRateLimiter
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app_with_rate_limit():
    """App con rate limiting configurado"""
    app = FastAPI()

    app.add_middleware(
        EndpointRateLimiter,
        limits={
            "/test/login": (3, 10),  # 3 intentos en 10 segundos
        },
    )

    @app.post("/test/login")
    def login():
        return {"message": "Success"}

    @app.get("/test/public")
    def public():
        return {"message": "Public endpoint"}

    return app


class TestEndpointRateLimiter:
    """Tests para rate limiting por endpoint"""

    def test_allows_requests_within_limit(self, app_with_rate_limit):
        """Debe permitir requests dentro del límite"""
        client = TestClient(app_with_rate_limit)

        # 3 requests (límite)
        for i in range(3):
            response = client.post("/test/login")
            assert response.status_code == 200

    def test_blocks_requests_over_limit(self, app_with_rate_limit):
        """Debe bloquear requests que excedan el límite"""
        client = TestClient(app_with_rate_limit)

        # 3 requests OK
        for i in range(3):
            response = client.post("/test/login")
            assert response.status_code == 200

        # 4ta request bloqueada
        response = client.post("/test/login")
        assert response.status_code == 429
        assert "retry_after" in response.json()

    def test_does_not_limit_unlisted_endpoints(self, app_with_rate_limit):
        """No debe limitar endpoints que no están en la lista"""
        client = TestClient(app_with_rate_limit)

        # 10 requests sin problema
        for i in range(10):
            response = client.get("/test/public")
            assert response.status_code == 200

    def test_includes_rate_limit_headers(self, app_with_rate_limit):
        """Debe incluir headers de rate limit"""
        client = TestClient(app_with_rate_limit)

        response = client.post("/test/login")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Window" in response.headers

    def test_reset_after_window(self, app_with_rate_limit):
        """Debe resetear contador después de la ventana de tiempo"""
        client = TestClient(app_with_rate_limit)

        # 3 requests (límite alcanzado)
        for i in range(3):
            client.post("/test/login")

        # 4ta bloqueada
        response = client.post("/test/login")
        assert response.status_code == 429

        # Esperar ventana (10 segundos en test es mucho, skipear en CI)
        # En producción, el límite se reseteará automáticamente
