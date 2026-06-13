"""Tests de integración del RequireCSRFMiddleware (punto 5 — CSRF en app real).

El middleware tiene bypass bajo pytest (coherente con auth); estos tests lo
DESACTIVAN con PYTEST_DISABLE_CSRF_BYPASS=1 para validar el comportamiento real:
- métodos seguros (GET) no requieren token,
- POST sin token válido → 403,
- POST con double-submit (header == cookie) → pasa,
- exenciones por sufijo (/auth/login...) y por segmento (/webhook/) → pasan sin token.

Se monta el middleware sobre una mini-app Starlette para no depender del flujo de
login completo: lo que se prueba es la política CSRF, no los endpoints concretos.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.middleware.require_csrf import RequireCSRFMiddleware

pytestmark = pytest.mark.no_db


async def _ok(request):  # noqa: ANN001
    return JSONResponse({"ok": True})


def _client() -> TestClient:
    app = Starlette(
        routes=[
            Route("/api/v1/tenant/expenses", _ok, methods=["GET", "POST"]),
            Route("/api/v1/tenant/auth/login", _ok, methods=["POST"]),
            Route("/api/v1/tenant/billing/webhook/stripe", _ok, methods=["POST"]),
        ]
    )
    app.add_middleware(RequireCSRFMiddleware)
    return TestClient(app)


@pytest.fixture(autouse=True)
def _force_csrf(monkeypatch):
    # Desactiva el bypass de CSRF bajo pytest para validar la protección real.
    monkeypatch.setenv("PYTEST_DISABLE_CSRF_BYPASS", "1")


def test_get_is_safe_and_needs_no_csrf():
    r = _client().get("/api/v1/tenant/expenses")
    assert r.status_code == 200


def test_post_without_csrf_is_rejected():
    r = _client().post("/api/v1/tenant/expenses", json={})
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]


def test_post_with_double_submit_passes():
    c = _client()
    c.cookies.set("csrf_token", "tok-123")
    r = c.post("/api/v1/tenant/expenses", json={}, headers={"X-CSRF-Token": "tok-123"})
    assert r.status_code == 200


def test_post_header_without_cookie_is_rejected():
    r = _client().post("/api/v1/tenant/expenses", json={}, headers={"X-CSRF-Token": "tok-123"})
    assert r.status_code == 403


def test_post_mismatched_token_is_rejected():
    c = _client()
    c.cookies.set("csrf_token", "cookie-tok")
    r = c.post("/api/v1/tenant/expenses", json={}, headers={"X-CSRF-Token": "other-tok"})
    assert r.status_code == 403


def test_login_suffix_is_exempt():
    r = _client().post("/api/v1/tenant/auth/login", json={})
    assert r.status_code == 200


def test_incoming_webhook_segment_is_exempt():
    # /webhook/ (singular) = webhook entrante externo, exento de CSRF.
    r = _client().post("/api/v1/tenant/billing/webhook/stripe", json={})
    assert r.status_code == 200
