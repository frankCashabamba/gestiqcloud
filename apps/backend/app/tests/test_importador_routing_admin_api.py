from uuid import uuid4

from fastapi.testclient import TestClient

from app.models.importador import ImpDocumento, ImpRoutingProfile
from app.models.tenant import Tenant
from app.modules.importador.services.document_routing_agent import (
    build_document_routing_decision,
    invalidate_document_routing_cache,
)
from app.modules.importador.services.document_routing_feedback_service import record_routing_signal


def _admin_headers(client: TestClient, superuser_factory) -> dict[str, str]:
    password = "admin123!"
    user = superuser_factory(
        username="routingadmin",
        email="routingadmin@example.com",
        password=password,
    )
    response = client.post(
        "/api/v1/admin/auth/login",
        json={"identificador": user.username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_importador_routing_requires_admin_scope(client: TestClient):
    response = client.get("/api/v1/admin/importador/routing/profiles")
    assert response.status_code == 403


def test_admin_importador_routing_profile_crud(client: TestClient, superuser_factory):
    headers = _admin_headers(client, superuser_factory)

    create_payload = {
        "code": "service_order",
        "document_type": "service_order",
        "description": "Orden de servicio",
        "suggested_destination": "expense",
        "required_groups": [["issue_date"], ["total_amount"], ["concept"]],
        "support_fields": ["vendor", "doc_number"],
        "explanation_fields": ["concept", "issue_date", "total_amount"],
        "blocked": False,
        "confidence_threshold": 0.82,
        "active": True,
    }
    created = client.post(
        "/api/v1/admin/importador/routing/profiles",
        json=create_payload,
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["item"]["code"] == "service_order"

    listed = client.get("/api/v1/admin/importador/routing/profiles", headers=headers)
    assert listed.status_code == 200
    assert any(item["code"] == "service_order" for item in listed.json())

    update_payload = dict(create_payload)
    update_payload["confidence_threshold"] = 0.9
    update_payload["description"] = "Orden de servicio actualizada"
    updated = client.put(
        "/api/v1/admin/importador/routing/profiles/service_order",
        json=update_payload,
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["item"]["confidence_threshold"] == 0.9

    deleted = client.delete(
        "/api/v1/admin/importador/routing/profiles/service_order",
        headers=headers,
    )
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


def test_admin_importador_routing_rule_create_invalidates_cache_and_enforces_uniqueness(
    client: TestClient, superuser_factory, db
):
    headers = _admin_headers(client, superuser_factory)
    tenant = Tenant(
        id=uuid4(),
        name="Routing Tenant",
        slug="routing-tenant",
        sector_template_name="panaderia",
    )
    db.add(tenant)
    db.add(
        ImpRoutingProfile(
            code="expense",
            document_type="expense",
            suggested_destination="expense",
            required_groups=[["issue_date"], ["total_amount"], ["concept"]],
            support_fields=["vendor"],
            explanation_fields=["concept", "issue_date", "total_amount"],
            blocked=False,
            confidence_threshold=0.8,
            active=True,
        )
    )
    db.commit()
    invalidate_document_routing_cache()

    baseline = build_document_routing_decision(
        source_doc_type="INVOICE",
        ai_confidence=0.95,
        extracted_data={
            "vendor": "Proveedor Demo",
            "issue_date": "2026-03-27",
            "total_amount": 42,
            "concept": "Taxi",
        },
        canonical_document={"fields": {}},
        category_keywords={"invoice": ["INVOICE"]},
        requires_review=False,
        db=db,
        tenant_id=tenant.id,
    )
    assert baseline.document_type == "supplier_invoice"

    payload = {
        "scope_kind": "tenant",
        "tenant_id": str(tenant.id),
        "source_kind": "doc_type",
        "source_key": "INVOICE",
        "profile_code": "expense",
        "priority": 5,
        "active": True,
    }
    created = client.post(
        "/api/v1/admin/importador/routing/rules",
        json=payload,
        headers=headers,
    )
    assert created.status_code == 200
    assert created.json()["item"]["profile_code"] == "expense"

    after = build_document_routing_decision(
        source_doc_type="INVOICE",
        ai_confidence=0.95,
        extracted_data={
            "vendor": "Proveedor Demo",
            "issue_date": "2026-03-27",
            "total_amount": 42,
            "concept": "Taxi",
        },
        canonical_document={"fields": {}},
        category_keywords={"invoice": ["INVOICE"]},
        requires_review=False,
        db=db,
        tenant_id=tenant.id,
    )
    assert after.document_type == "expense"
    assert after.suggested_destination == "expense"

    duplicate = client.post(
        "/api/v1/admin/importador/routing/rules",
        json=payload,
        headers=headers,
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "routing_rule_scope_conflict"


def test_admin_importador_routing_preview_resolves_sector_rule(
    client: TestClient, superuser_factory, db
):
    headers = _admin_headers(client, superuser_factory)
    db.add(
        ImpRoutingProfile(
            code="service_order",
            document_type="service_order",
            suggested_destination="expense",
            required_groups=[["issue_date"], ["total_amount"], ["concept"]],
            support_fields=["vendor", "doc_number"],
            explanation_fields=["concept", "issue_date", "total_amount"],
            blocked=False,
            confidence_threshold=0.82,
            active=True,
        )
    )
    db.commit()
    invalidate_document_routing_cache()

    rule_created = client.post(
        "/api/v1/admin/importador/routing/rules",
        json={
            "scope_kind": "sector",
            "sector": "panaderia",
            "source_kind": "doc_type",
            "source_key": "SERVICE_ORDER",
            "profile_code": "service_order",
            "priority": 10,
            "active": True,
        },
        headers=headers,
    )
    assert rule_created.status_code == 200

    preview = client.post(
        "/api/v1/admin/importador/routing/preview",
        json={
            "scope_kind": "sector",
            "sector": "panaderia",
            "source_doc_type": "SERVICE_ORDER",
            "ai_confidence": 0.93,
            "extracted_data": {
                "vendor": "Proveedor Demo",
                "issue_date": "2026-03-27",
                "total_amount": 120.5,
                "concept": "Reparacion de horno",
            },
        },
        headers=headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["profile_code"] == "service_order"
    assert body["matched_scope"] == "sector"
    assert body["matched_by"] == "doc_type:service_order"
    assert body["rule_source_kind"] == "doc_type"
    assert body["rule_source_key"] == "SERVICE_ORDER"
    assert body["resolved_sector"] == "panaderia"
    assert body["decision"]["document_type"] == "service_order"
    assert body["decision"]["suggested_destination"] == "expense"
    assert body["decision"]["required_fields_ok"] is True


def test_admin_importador_routing_preview_can_use_real_document(
    client: TestClient, superuser_factory, db
):
    headers = _admin_headers(client, superuser_factory)
    tenant = Tenant(
        id=uuid4(),
        name="Preview Tenant",
        slug="preview-tenant",
        sector_template_name="panaderia",
    )
    doc = ImpDocumento(
        id=uuid4(),
        tenant_id=tenant.id,
        nombre_archivo="factura-demo.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=1024,
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.94,
        requiere_revision=False,
        datos_extraidos={
            "vendor": "Proveedor Real",
            "issue_date": "2026-03-27",
            "total_amount": 199.5,
            "concept": "Harina",
        },
        estado="REVIEW",
        proveedor_detectado="Proveedor Real",
        monto_total=199.5,
        raw_ai_json={"canonical_document": {"fields": {"doc_number": "FAC-1"}}},
    )
    db.add(tenant)
    db.add(doc)
    db.commit()
    invalidate_document_routing_cache()

    listed = client.get(
        f"/api/v1/admin/importador/routing/documents?tenant_id={tenant.id}",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(item["id"] == str(doc.id) for item in listed.json())

    preview = client.post(
        "/api/v1/admin/importador/routing/preview",
        json={
            "scope_kind": "tenant",
            "document_id": str(doc.id),
        },
        headers=headers,
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["document_id"] == str(doc.id)
    assert body["document_name"] == "factura-demo.pdf"
    assert body["tenant_id"] == str(tenant.id)
    assert body["decision"]["document_type"] == "supplier_invoice"
    assert body["decision"]["required_fields_ok"] is True


def test_admin_importador_routing_learning_insights_returns_suggestions(
    client: TestClient, superuser_factory, db
):
    headers = _admin_headers(client, superuser_factory)
    tenant = Tenant(
        id=uuid4(),
        name="Insights Tenant",
        slug="insights-tenant",
        sector_template_name="panaderia",
    )
    db.add(tenant)
    db.commit()

    doc_a = ImpDocumento(
        id=uuid4(),
        tenant_id=tenant.id,
        nombre_archivo="invoice-a.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=64,
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.72,
        requiere_revision=True,
        datos_confirmados={
            "vendor": "Proveedor Uno",
            "issue_date": "2026-03-27",
            "total_amount": 50,
        },
        estado="CONFIRMED",
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    doc_b = ImpDocumento(
        id=uuid4(),
        tenant_id=tenant.id,
        nombre_archivo="invoice-b.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=64,
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.93,
        requiere_revision=False,
        datos_confirmados={
            "vendor": "Proveedor Dos",
            "issue_date": "2026-03-28",
            "total_amount": 80,
            "currency": "USD",
        },
        estado="IMPORTED",
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    db.add_all([doc_a, doc_b])
    db.commit()

    record_routing_signal(
        db,
        doc_a,
        user_id="tester",
        event="confirm",
        changed_fields=["issue_date", "total_amount"],
    )
    record_routing_signal(
        db,
        doc_b,
        user_id="tester",
        event="save",
        chosen_destination="supplier_invoice",
        payload={"status": "created"},
    )
    db.commit()

    response = client.get(
        f"/api/v1/admin/importador/routing/learning-insights?tenant_id={tenant.id}&source_doc_type=INVOICE",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    insight = body[0]
    assert insight["source_doc_type"] == "INVOICE"
    assert insight["document_type"] == "supplier_invoice"
    assert insight["signals_count"] >= 2
    assert "issue_date" in insight["top_changed_fields"]
    assert "total_amount" in insight["top_changed_fields"]
    assert insight["suggested_confidence_threshold"] >= 0.55


def test_admin_importador_routing_learning_proposal_returns_profile_payload(
    client: TestClient, superuser_factory, db
):
    headers = _admin_headers(client, superuser_factory)
    tenant = Tenant(
        id=uuid4(),
        name="Proposal Tenant",
        slug="proposal-tenant",
        sector_template_name="panaderia",
    )
    profile = ImpRoutingProfile(
        code="supplier_invoice",
        document_type="supplier_invoice",
        suggested_destination="supplier_invoice",
        required_groups=[["issue_date"]],
        support_fields=["vendor"],
        explanation_fields=["vendor", "issue_date"],
        blocked=False,
        confidence_threshold=0.8,
        active=True,
    )
    doc = ImpDocumento(
        id=uuid4(),
        tenant_id=tenant.id,
        nombre_archivo="invoice-proposal.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=64,
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.9,
        requiere_revision=False,
        datos_confirmados={
            "vendor": "Proveedor Tres",
            "issue_date": "2026-03-28",
            "total_amount": 100,
            "currency": "USD",
        },
        estado="IMPORTED",
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    db.add_all([tenant, profile, doc])
    db.commit()

    record_routing_signal(
        db,
        doc,
        user_id="tester",
        event="save",
        chosen_destination="supplier_invoice",
        changed_fields=["total_amount"],
        payload={"status": "created"},
    )
    db.commit()

    response = client.get(
        f"/api/v1/admin/importador/routing/learning-insights/proposal?profile_code=supplier_invoice&tenant_id={tenant.id}&source_doc_type=INVOICE&document_type=supplier_invoice",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["profile_code"] == "supplier_invoice"
    assert body["current_profile"]["code"] == "supplier_invoice"
    assert body["proposed_update"]["code"] == "supplier_invoice"
    assert body["proposed_update"]["document_type"] == "supplier_invoice"
    assert body["proposed_update"]["confidence_threshold"] >= 0.55
    assert "total_amount" in ",".join(
        field for group in body["proposed_update"]["required_groups"] for field in group
    )
