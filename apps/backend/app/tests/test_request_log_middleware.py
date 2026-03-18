from fastapi import FastAPI, Request
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
