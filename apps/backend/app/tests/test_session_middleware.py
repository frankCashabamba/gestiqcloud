from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.sessions import SessionMiddlewareServerSide, SessionStore


class ExplodingStore(SessionStore):
    async def create(
        self, sid: str, data: dict[str, Any], ttl: int
    ) -> None:  # pragma: no cover - not used
        raise RuntimeError("boom")

    async def get(self, sid: str) -> dict[str, Any]:
        raise RuntimeError("boom")

    async def set(self, sid: str, data: dict[str, Any], ttl: int) -> None:
        raise RuntimeError("boom")

    async def delete(self, sid: str) -> None:  # pragma: no cover - not used
        raise RuntimeError("boom")


def _build_app() -> FastAPI:
    os.environ.setdefault("FRONTEND_URL", "http://test.local")
    os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
    os.environ.setdefault("TENANT_NAMESPACE_UUID", "00000000-0000-0000-0000-000000000000")

    app = FastAPI()
    app.add_middleware(
        SessionMiddlewareServerSide,
        cookie_name="sess",
        secret_key="secret",
        https_only=False,
        store=ExplodingStore(),
        ttl_seconds=30,
        fallback_window_seconds=60,
    )

    @app.get("/write")
    def write(request: Request) -> JSONResponse:
        request.state.session["foo"] = "bar"
        request.state.session_dirty = True
        return JSONResponse({"ok": True})

    @app.get("/read")
    def read(request: Request) -> JSONResponse:
        return JSONResponse({"session": dict(getattr(request.state, "session", {}))})

    return app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(_build_app())


def test_session_middleware_falls_back_to_memory_store(client: TestClient) -> None:
    first = client.get("/write")
    assert first.status_code == 200
    cookie = first.cookies.get("sess")
    assert cookie is not None

    second = client.get("/read", cookies={"sess": cookie})
    assert second.status_code == 200
    assert second.json()["session"].get("foo") == "bar"
