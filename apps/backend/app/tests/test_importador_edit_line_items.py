from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models.importador import ImpDocumento
from app.modules.importador.router import edit_document_fields
from app.modules.importador.schemas import EditFieldsRequest


def _fake_request(tenant_id) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={"tenant_id": str(tenant_id), "user_id": "tester", "is_company_admin": True},
        )
    )


def test_edit_document_fields_supports_line_items_and_infers_total(db: Session, tenant_minimal):
    tenant_id = tenant_minimal["tenant_id"]

    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="nota-venta.jpeg",
        tipo_archivo="JPG",
        tamanio_bytes=256,
        estado="REVIEW",
        tipo_documento_detectado="INVOICE",
        datos_extraidos={
            "doc_number": "NOTA DE VENTA N°",
            "issue_date": "2016-03-24",
            "line_items": [],
        },
        raw_ai_json={},
    )
    db.add(document)
    db.commit()

    result = edit_document_fields(
        document.id,
        EditFieldsRequest(
            campos={
                "line_items": [
                    {
                        "description": "Big 225",
                        "quantity": "1",
                        "unit_price": "5.35",
                        "total_price": "",
                    },
                    {"description": "Cifrut 1700", "quantity": "1", "unit_price": "5.30"},
                    {"description": "Amper", "quantity": "1", "unit_price": "5.30"},
                ]
            }
        ),
        request=_fake_request(tenant_id),
        db=db,
    )

    db.refresh(document)

    assert result.datos_extraidos["line_items"][0]["description"] == "Big 225"
    assert result.datos_extraidos["line_items"][0]["total_price"] == 5.35
    assert result.datos_extraidos["line_items"][1]["unit_price"] == 5.3
    assert result.datos_extraidos["total_amount"] == 15.95
    assert document.monto_total == 15.95
    assert document.raw_ai_json["canonical_document"]


def test_edit_document_fields_preserves_extra_columns_and_promotes_supplier_ref(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    monkeypatch.setattr(
        "app.modules.importador.router.get_field_aliases",
        lambda _db, tenant_id=None: {
            "line_items": ["line_items"],
            "total_amount": ["total_amount"],
            "supplier_ref": ["Ref."],
        },
    )

    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-bazar.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=256,
        estado="REVIEW",
        tipo_documento_detectado="INVOICE",
        datos_extraidos={"line_items": []},
        raw_ai_json={},
    )
    db.add(document)
    db.commit()

    result = edit_document_fields(
        document.id,
        EditFieldsRequest(
            campos={
                "line_items": [
                    {
                        "description": "Set de tazas de ceramica 350 ml",
                        "quantity": "24",
                        "unit_price": "2.35",
                        "extra_columns": {"Ref.": "REF-BZ-1042"},
                    }
                ]
            }
        ),
        request=_fake_request(tenant_id),
        db=db,
    )

    row = result.datos_extraidos["line_items"][0]
    assert row["supplier_ref"] == "REF-BZ-1042"
    assert "extra_columns" not in row
