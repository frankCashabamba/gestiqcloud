from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.importador import ImpDocumento
from app.models.importador import ImpRoutingRule
from app.models.tenant import Tenant
from app.modules.importador.router import SaveDocumentRequest, _infer_save_destination, save_document
from app.modules.importador.services.document_routing_agent import (
    build_document_routing_decision,
    invalidate_document_routing_cache,
)


@pytest.mark.no_db
def test_document_routing_agent_returns_ready_supplier_invoice():
    decision = build_document_routing_decision(
        source_doc_type="INVOICE",
        ai_confidence=0.93,
        extracted_data={
            "vendor": "Molino Central",
            "issue_date": "2026-03-27",
            "subtotal": 100,
            "tax_amount": 12,
            "total_amount": 112,
        },
        canonical_document={"fields": {"currency": "USD"}},
        category_keywords={"invoice": ["INVOICE"]},
        requires_review=False,
    )

    assert decision.document_type == "supplier_invoice"
    assert decision.suggested_destination == "supplier_invoice"
    assert decision.required_fields_ok is True
    assert decision.needs_human_review is False
    assert decision.confidence >= 0.9
    assert "proveedor" in decision.reason.lower()


@pytest.mark.no_db
def test_document_routing_agent_requests_review_when_invoice_fields_are_missing():
    decision = build_document_routing_decision(
        source_doc_type="INVOICE",
        ai_confidence=0.94,
        extracted_data={"vendor": "Molino Central"},
        canonical_document={"fields": {}},
        category_keywords={"invoice": ["INVOICE"]},
        requires_review=False,
    )

    assert decision.document_type == "supplier_invoice"
    assert decision.required_fields_ok is False
    assert decision.needs_human_review is True
    assert decision.missing_fields == ["issue_date", "total_amount"]
    assert decision.confidence < 0.8


def test_infer_save_destination_uses_routing_over_supplier_metadata_fallback(db):
    doc = SimpleNamespace(
        tipo_documento_detectado="RECEIPT",
        confianza_clasificacion=0.91,
        requiere_revision=False,
        proveedor_detectado="Proveedor demo",
        ruc_detectado="1234567890",
        monto_total=45.5,
        datos_confirmados={"issue_date": "2026-03-27", "total_amount": 45.5, "concept": "Taxi"},
        datos_extraidos=None,
        raw_ai_json={"canonical_document": {"fields": {"issue_date": "2026-03-27"}}},
    )

    destination = _infer_save_destination(doc, db)

    assert destination == "expense"


def _fake_request(tenant_id):
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={"tenant_id": str(tenant_id), "user_id": str(uuid4())},
        )
    )


def test_save_document_returns_409_when_required_fields_are_missing_for_destination(
    db, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-incompleta.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=64,
        estado="CONFIRMED",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.96,
        requiere_revision=False,
        datos_confirmados={"vendor": "Molino Central"},
        raw_ai_json={"canonical_document": {"fields": {"vendor": "Molino Central"}}},
    )
    db.add(document)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        save_document(
            document.id,
            SaveDocumentRequest(destination="supplier_invoice"),
            _fake_request(tenant_id),
            db,
        )

    exc = exc_info.value
    assert exc.status_code == 409
    detail = exc.detail
    assert detail["code"] == "document_routing_review_required"
    assert detail["required_fields_ok"] is False
    assert detail["missing_fields"] == ["issue_date", "total_amount"]


def test_document_routing_uses_tenant_rule_before_sector_and_system(db):
    tenant_id = uuid4()
    tenant = Tenant(
        id=tenant_id,
        name="Routing Override Co",
        slug=f"routing-{tenant_id.hex[:8]}",
        sector_template_name="panaderia",
    )
    db.add(tenant)
    db.flush()

    db.add_all(
        [
            ImpRoutingRule(
                sector="panaderia",
                source_kind="doc_type",
                source_key="INVOICE",
                profile_code="supplier_invoice",
                priority=20,
            ),
            ImpRoutingRule(
                tenant_id=tenant_id,
                source_kind="doc_type",
                source_key="INVOICE",
                profile_code="expense",
                priority=5,
            ),
        ]
    )
    db.commit()
    invalidate_document_routing_cache()

    decision = build_document_routing_decision(
        source_doc_type="INVOICE",
        ai_confidence=0.96,
        extracted_data={
            "vendor": "Proveedor Demo",
            "issue_date": "2026-03-27",
            "total_amount": 55,
            "concept": "Taxi",
        },
        canonical_document={"fields": {}},
        category_keywords={"invoice": ["INVOICE"]},
        requires_review=False,
        db=db,
        tenant_id=tenant_id,
    )

    assert decision.document_type == "expense"
    assert decision.suggested_destination == "expense"
