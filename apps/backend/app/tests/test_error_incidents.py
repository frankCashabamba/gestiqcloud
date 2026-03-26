from starlette.requests import Request

from app.main import _record_auto_incident


class _FakeSession:
    def __init__(self):
        self.added = []
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True


def _build_request() -> Request:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/test/fail",
            "headers": [],
            "query_string": b"foo=bar",
            "client": ("127.0.0.1", 12345),
        }
    )
    request.state.access_claims = {
        "tenant_id": "ec2cbc37-439c-4045-a153-260ec9e4dfa7",
        "user_id": "a1431ce8-2646-4039-b8c0-74a4c8e209c3",
    }
    request.state.request_id = "req-123"
    return request


def test_record_auto_incident_persists_tenant_error(monkeypatch):
    fake_session = _FakeSession()
    monkeypatch.setattr("app.config.database.SessionLocal", lambda: fake_session)

    request = _build_request()
    try:
        raise RuntimeError("boom")
    except RuntimeError as exc:
        _record_auto_incident(request, exc)

    assert fake_session.committed is True
    assert len(fake_session.added) == 1
    incident = fake_session.added[0]
    assert incident.tenant_id == "ec2cbc37-439c-4045-a153-260ec9e4dfa7"
    assert incident.type == "error"
    assert incident.auto_detected is True
    assert incident.context["req_id"] == "req-123"
    assert incident.context["path"] == "/api/v1/test/fail"
