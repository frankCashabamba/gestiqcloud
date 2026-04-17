from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.models.importador import ImpDocumento, ImpRoutingSignal
from app.modules.importador import crud
from app.modules.importador.router import ConfirmRequest, confirm_document, list_documents
from app.modules.importador.services.document_routing_feedback_service import record_routing_signal


def _fake_request(tenant_id, user_id: str = "tester"):
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={
                "tenant_id": str(tenant_id),
                "user_id": user_id,
                "is_company_admin": True,
            },
        )
    )


def test_record_routing_signal_persists_snapshot_and_payload(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-feedback.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=32,
        estado="CONFIRMED",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.96,
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

    signal = record_routing_signal(
        db,
        document,
        user_id="user-1",
        event="save",
        chosen_destination="supplier_invoice",
        payload={"status": "created", "record_id": str(uuid4())},
    )
    db.commit()

    stored = db.get(ImpRoutingSignal, signal.id)
    assert stored is not None
    assert stored.event == "save"
    assert stored.chosen_destination == "supplier_invoice"
    assert stored.routing_snapshot["document_type"] == "supplier_invoice"
    assert stored.payload["status"] == "created"

    # raw_ai_json ya no almacena routing/routing_feedback (era redundante y solo guardaba
    # el último evento). La fuente de verdad es ImpRoutingSignal (ya validado arriba).
    db.refresh(document)
    assert "routing_feedback" not in (document.raw_ai_json or {})


def test_confirm_document_creates_routing_signal_row(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="confirm-feedback.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=32,
        estado="REVIEW",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.92,
        requiere_revision=False,
        datos_extraidos={"vendor": "Proveedor Demo"},
        raw_ai_json={"canonical_document": {"fields": {}}},
    )
    db.add(document)
    db.commit()

    response = confirm_document(
        document.id,
        ConfirmRequest(
            datos_confirmados={
                "vendor": "Proveedor Demo",
                "issue_date": "2026-03-27",
                "total_amount": 99.5,
            }
        ),
        _fake_request(tenant_id),
        db,
    )

    signals = (
        db.query(ImpRoutingSignal)
        .filter(ImpRoutingSignal.documento_id == document.id)
        .order_by(ImpRoutingSignal.created_at.asc())
        .all()
    )
    assert response.estado == "CONFIRMED"
    assert response.last_confirmation_mode == "corrected_by_user"
    assert len(signals) == 1
    assert signals[0].event == "confirm"
    assert signals[0].routing_snapshot["required_fields_ok"] is True
    assert signals[0].changed_fields == ["issue_date", "total_amount", "vendor"]
    logs = [log for log in response.logs if log.accion == "CONFIRM"]
    assert len(logs) == 1
    assert logs[0].detalle["confirmation_mode"] == "corrected_by_user"


def test_list_documents_exposes_learning_reprocess_metadata(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="learning-refresh.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=32,
        estado="REVIEW",
        tipo_documento_detectado="INVOICE",
        confianza_clasificacion=0.88,
        requiere_revision=True,
        datos_extraidos={"vendor": "Proveedor Demo"},
    )
    db.add(document)
    db.commit()

    crud.add_log(
        db,
        document.id,
        "REPROCESS",
        "tester",
        {"reason": "learning_update", "mode": "async"},
    )
    db.commit()

    docs = list_documents(_fake_request(tenant_id), estado=None, limit=50, offset=0, db=db)

    assert len(docs) == 1
    assert docs[0].id == document.id
    assert docs[0].last_processing_reason == "learning_update"
    assert docs[0].last_learning_reprocess_at is not None
