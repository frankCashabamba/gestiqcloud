from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models.ai.incident import Incident


def _admin_headers(client: TestClient, superuser_factory) -> dict[str, str]:
    password = secrets.token_urlsafe(12)
    superuser_factory(email="incidents-admin@example.com", username="incadmin", password=password)
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": "incadmin", "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_incidents_list_analyze_and_resolve(
    client: TestClient,
    db,
    superuser_factory,
    tenant_minimal,
    monkeypatch,
):
    tenant_id = tenant_minimal["tenant_id"]
    incident = Incident(
        tenant_id=tenant_id,
        type="warning",
        severity="medium",
        title="Importador: factura guardada con líneas sin stock",
        description="Quedaron líneas pendientes.",
        context={"document_id": "doc-1"},
        auto_detected=True,
        status="open",
        created_at=datetime.now(UTC),
    )
    db.add(incident)
    db.commit()

    headers = _admin_headers(client, superuser_factory)

    list_response = client.get("/api/v1/admin/incidents?status=open", headers=headers)
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(incident.id)
    assert payload[0]["title"] == incident.title

    async def _fake_analyze(**kwargs):
        target = db.query(Incident).filter(Incident.id == incident.id).first()
        target.ia_analysis = {"root_cause": "missing product linkage"}
        target.ia_suggestion = "Create or link the missing product before updating stock."
        db.commit()
        return {
            "incident_id": incident.id,
            "analysis": target.ia_analysis,
            "suggestion": target.ia_suggestion,
            "confidence_score": 0.91,
            "processing_time_ms": 12,
        }

    monkeypatch.setattr(
        "app.modules.support.interface.http.incidents.analyze_incident_with_ia",
        _fake_analyze,
    )

    analyze_response = client.post(
        f"/api/v1/admin/incidents/{incident.id}/analyze",
        headers=headers,
        json={"use_gpt4": False, "include_code_suggestions": True},
    )
    assert analyze_response.status_code == 200
    analyzed = analyze_response.json()
    assert analyzed["analysis"]["root_cause"] == "missing product linkage"
    assert analyzed["suggestion"] == "Create or link the missing product before updating stock."

    get_response = client.get(f"/api/v1/admin/incidents/{incident.id}", headers=headers)
    assert get_response.status_code == 200
    detailed = get_response.json()
    assert detailed["ia_analysis"]["root_cause"] == "missing product linkage"
    assert detailed["ia_suggestion"] == "Create or link the missing product before updating stock."

    resolve_response = client.post(
        f"/api/v1/admin/incidents/{incident.id}/resolve",
        headers=headers,
    )
    assert resolve_response.status_code == 200

    db.refresh(incident)
    assert incident.status == "resolved"
    assert incident.auto_resolved is True
