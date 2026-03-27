from __future__ import annotations

from uuid import uuid4

from app.models.core.audit_event import AuditEvent
from app.models.importador import ImpDocumento


def test_auto_audit_serializes_uuid_changes_in_sqlite(db, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="audit-uuid.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=32,
        estado="REVIEW",
    )
    db.add(document)
    db.commit()

    target_id = uuid4()
    document.saved_record_id = target_id
    db.commit()

    event = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == "ImpDocumento",
            AuditEvent.entity_id == str(document.id),
            AuditEvent.action == "update",
        )
        .order_by(AuditEvent.created_at.desc())
        .first()
    )

    assert event is not None
    assert isinstance(event.changes, dict)
    assert event.changes["saved_record_id"]["new"] == str(target_id)
