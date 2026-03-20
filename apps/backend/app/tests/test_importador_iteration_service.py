from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento, ImpStagingLine
from app.modules.importador.schemas import IterationScopeIn
from app.modules.importador.services.iteration_service import (
    fetch_lines_for_scope,
    run_iteration,
    upsert_staging_lines_from_extraction,
)


def test_upsert_staging_lines_from_extraction_is_idempotent_for_non_tabular_docs(
    db: Session, tenant_minimal
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-non-tabular.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
    )
    db.add(document)
    db.commit()

    payload = {"vendor": "Proveedor Demo", "total_amount": 120.5}

    inserted_first = upsert_staging_lines_from_extraction(db, document.id, tenant_id, payload)
    inserted_second = upsert_staging_lines_from_extraction(db, document.id, tenant_id, payload)
    db.commit()

    rows = (
        db.query(ImpStagingLine)
        .filter(ImpStagingLine.documento_id == document.id)
        .order_by(ImpStagingLine.line_number.asc())
        .all()
    )

    assert inserted_first == 1
    assert inserted_second == 0
    assert len(rows) == 1
    assert rows[0].sheet_name == "__document__"


def test_fetch_lines_for_scope_matches_any_selected_field(db: Session, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-scope.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
    )
    db.add(document)
    db.flush()

    db.add_all(
        [
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=1,
                sheet_name="__document__",
                raw_data={"vendor": "A"},
                estado="REPROCESS",
                campos_revision=["vendor"],
            ),
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=2,
                sheet_name="__document__",
                raw_data={"total_amount": 10},
                estado="REPROCESS",
                campos_revision=["total_amount"],
            ),
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=3,
                sheet_name="__document__",
                raw_data={"currency": "PEN"},
                estado="REPROCESS",
                campos_revision=["currency"],
            ),
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=4,
                sheet_name="__document__",
                raw_data={"fallback": True},
                estado="REPROCESS",
                campos_revision=None,
            ),
        ]
    )
    db.commit()

    scope = IterationScopeIn(mode="SELECTIVE", filter_campos=["vendor", "total_amount"])
    lines = fetch_lines_for_scope(db, document.id, scope)

    assert [line.line_number for line in lines] == [1, 2, 4]


def test_fetch_lines_for_scope_matches_selected_columns(db: Session, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-columns.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
    )
    db.add(document)
    db.flush()

    db.add_all(
        [
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=1,
                sheet_name="__document__",
                raw_data={"vendor": "A"},
                estado="REPROCESS",
            ),
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=2,
                sheet_name="__document__",
                raw_data={"doc_number": "F001-1"},
                normalized_data={"vendor_tax_id": "20100099991"},
                estado="REPROCESS",
            ),
            ImpStagingLine(
                tenant_id=tenant_id,
                documento_id=document.id,
                line_number=3,
                sheet_name="__document__",
                raw_data={"notes": "manual review"},
                estado="REPROCESS",
            ),
        ]
    )
    db.commit()

    scope = IterationScopeIn(
        mode="SELECTIVE",
        filter_columns=["vendor_tax_id", "notes"],
    )
    lines = fetch_lines_for_scope(db, document.id, scope)

    assert [line.line_number for line in lines] == [2, 3]


def test_run_iteration_reextracts_document_scope_fields_and_syncs_document(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-image.jpg",
        tipo_archivo="JPG",
        tamanio_bytes=128,
        estado="REVIEW",
        tipo_documento_detectado="INVOICE",
        texto_ocr="Proveedor MOLINOS MIRAFLORES S.A. moneda PEN cliente Cliente Corregido",
        datos_extraidos={"currency": "S/.", "customer": "2az6n Social / Nombres y Apellidos"},
    )
    db.add(document)
    db.flush()

    line = ImpStagingLine(
        tenant_id=tenant_id,
        documento_id=document.id,
        line_number=1,
        sheet_name="__document__",
        raw_data={"currency": "S/.", "customer": "2az6n Social / Nombres y Apellidos"},
        estado="REPROCESS",
    )
    db.add(line)
    db.commit()

    async def _fake_analyze_document(*args, **kwargs):
        del args, kwargs
        return {
            "doc_type": "INVOICE",
            "confidence": 0.95,
            "reasoning": "focused re-extraction",
            "fields": {
                "currency": "PEN",
                "customer": "Cliente Corregido",
            },
            "model_used": "test-model",
            "prompt_sent": "",
            "raw_response": "{}",
        }

    monkeypatch.setattr(
        "app.modules.importador.services.iteration_service.analyze_document",
        _fake_analyze_document,
    )

    result = run_iteration(
        db,
        document,
        tenant_id,
        "tester",
        IterationScopeIn(
            mode="SELECTIVE",
            filter_columns=["currency", "customer"],
            filter_lines=[1],
        ),
        field_aliases={
            "currency": ["currency"],
            "customer": ["customer"],
        },
        canonical_fields={
            "currency": {"type": "text"},
            "customer": {"type": "text"},
        },
    )
    db.commit()
    db.refresh(document)
    db.refresh(line)

    assert result.lines_imported == 1
    assert document.datos_extraidos["currency"] == "PEN"
    assert document.datos_extraidos["customer"] == "Cliente Corregido"
    assert line.normalized_data["currency"] == "PEN"
    assert line.normalized_data["customer"] == "Cliente Corregido"
