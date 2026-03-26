import logging

from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from app.core.log_context import get_request_context
from app.middleware.request_log import RequestLogMiddleware


def test_request_log_middleware_sets_header_and_records_metrics(monkeypatch):
    recorded: list[tuple[str, str, int, float]] = []

    def fake_record_request(method: str, endpoint: str, status: int, duration: float) -> None:
        recorded.append((method, endpoint, status, duration))

    monkeypatch.setattr("app.middleware.request_log.record_request", fake_record_request)

    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/ping")
    async def ping(request: Request):
        request.state.access_claims = {"tenant_id": "tenant-123", "user_id": "user-456"}
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/ping", headers={"X-Request-ID": "req-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-123"
    assert recorded
    assert recorded[0][0] == "GET"
    assert recorded[0][1] == "/ping"
    assert recorded[0][2] == 200
    assert recorded[0][3] >= 0
    assert get_request_context() is None


def test_request_log_middleware_skips_success_logs_by_default(caplog):
    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/ping")

    assert response.status_code == 200
    assert not [record for record in caplog.records if record.name == "app.request"]


def test_request_log_middleware_logs_4xx_when_threshold_is_lowered(monkeypatch, caplog):
    monkeypatch.setenv("REQUEST_LOG_MIN_STATUS", "400")

    app = FastAPI()
    app.add_middleware(RequestLogMiddleware)

    @app.get("/missing")
    async def missing():
        return Response(status_code=404)

    client = TestClient(app)
    with caplog.at_level(logging.WARNING, logger="app.request"):
        response = client.get("/missing")

    assert response.status_code == 404
    assert any(record.levelno == logging.WARNING for record in caplog.records)
