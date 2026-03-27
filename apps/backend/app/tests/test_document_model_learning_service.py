from __future__ import annotations

from app.models.importador import ImpDocumento
from app.modules.importador.services.document_model_learning_service import (
    build_signal_learning_recipe_config,
    summarize_learning_rerun,
)
from app.modules.importador.services.document_routing_feedback_service import record_routing_signal


def test_build_signal_learning_recipe_config_uses_recent_feedback(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="invoice-learning.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=64,
        estado="CONFIRMED",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.94,
        requiere_revision=False,
        datos_confirmados={
            "vendor": "Proveedor Demo",
            "issue_date": "2026-03-27",
            "total_amount": 125.5,
        },
        raw_ai_json={"canonical_document": {"fields": {"doc_number": "F-001"}}},
    )
    db.add(document)
    db.commit()

    record_routing_signal(
        db,
        document,
        user_id="tester",
        event="confirm",
        changed_fields=["issue_date", "total_amount"],
    )
    db.commit()

    config = build_signal_learning_recipe_config(
        db,
        tenant_id=tenant_id,
        source_doc_type="INVOICE",
        base_recipe_config={"prompt_user": "Base prompt"},
    )

    assert "field_descriptions" in config
    assert "issue_date" in config["field_descriptions"]
    assert "total_amount" in config["field_descriptions"]
    assert "Learning signals from user corrections" in config["prompt_user"]
    assert "supplier_invoice" in config["prompt_user"]
    assert config["_signal_learning"]["signals_used"] == 1
    assert config["_signal_learning"]["source_doc_type"] == "INVOICE"


def test_build_signal_learning_recipe_config_prefers_high_quality_matching_signals(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    invoice_doc = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="invoice-a.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=10,
        estado="IMPORTED",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.97,
        requiere_revision=False,
        datos_confirmados={"vendor": "Proveedor A", "issue_date": "2026-03-27", "total_amount": 10},
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    receipt_doc = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="receipt-a.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=10,
        estado="CONFIRMED",
        tipo_documento_detectado="RECEIPT",
        confianza_clasificacion=0.75,
        requiere_revision=True,
        datos_confirmados={"concept": "Taxi", "total_amount": 5},
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    db.add_all([invoice_doc, receipt_doc])
    db.commit()

    record_routing_signal(
        db,
        invoice_doc,
        user_id="tester",
        event="save",
        chosen_destination="supplier_invoice",
        changed_fields=["issue_date"],
    )
    record_routing_signal(
        db,
        receipt_doc,
        user_id="tester",
        event="edit",
        changed_fields=["concept"],
    )
    db.commit()

    config = build_signal_learning_recipe_config(
        db,
        tenant_id=tenant_id,
        source_doc_type="INVOICE",
        base_recipe_config={},
    )

    assert config["_signal_learning"]["signals_used"] == 1
    assert config["_signal_learning"]["top_document_type"] == "supplier_invoice"
    assert "concept" not in config.get("field_descriptions", {})


def test_summarize_learning_rerun_returns_improvement_deltas():
    summary = summarize_learning_rerun(
        baseline_doc_type="INVOICE",
        baseline_confidence=0.71,
        baseline_fields={"vendor": "Proveedor", "issue_date": ""},
        baseline_routing={
            "document_type": "expense",
            "suggested_destination": "expense",
            "missing_fields": ["total_amount"],
            "required_fields_ok": False,
        },
        rerun_doc_type="INVOICE",
        rerun_confidence=0.89,
        rerun_fields={"vendor": "Proveedor", "issue_date": "2026-03-27", "total_amount": 25},
        rerun_routing={
            "document_type": "supplier_invoice",
            "suggested_destination": "supplier_invoice",
            "missing_fields": [],
            "required_fields_ok": True,
        },
        signal_learning_meta={"signals_used": 3},
    )

    assert summary["improved"] is True
    assert summary["confidence_delta"] > 0
    assert summary["field_count_delta"] > 0
    assert summary["missing_fields_delta"] > 0
    assert summary["destination_changed"] is True
