from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.orm import Session

from app.models.importador import IcuRecipeSnapshot, ImpDocumento
from app.modules.importador.auto_recipe import resolve_auto_recipe_from_text
from app.modules.importador.tasks import _run_processing

pytestmark = pytest.mark.usefixtures("requires_postgres")


class _SessionFactory:
    def __init__(self, session: Session):
        self._session = session

    def __call__(self):
        return self

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_run_processing_reuses_text_snapshot_learning_for_async_flow(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    _, snapshot_id, _, _, _ = resolve_auto_recipe_from_text(
        db,
        tenant_id,
        "INVOICE",
        {"currency": "PEN", "total_amount": 2145.0},
        "PDF",
        "tester",
    )
    assert snapshot_id is not None

    snapshot = db.get(IcuRecipeSnapshot, snapshot_id)
    assert snapshot is not None
    content = dict(snapshot.content_json or {})
    content["field_descriptions"] = {
        "payment_method": "Recent confirmed example: Transferencia bancaria. Extract the exact printed payment method when visible.",
    }
    content["learning_prompt_user"] = (
        "Learning from confirmed similar documents:\n"
        "- 'payment_method' was confirmed repeatedly in similar documents."
    )
    snapshot.content_json = content

    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-aprendizaje.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="PENDING",
        usuario_id="tester",
    )
    db.add(document)
    db.commit()

    async def fake_extract_text_from_file(_file_bytes: bytes, _filename: str):
        return {
            "text": "Factura de proveedor con forma de pago transferencia bancaria",
            "structured_data": None,
            "format": "PDF",
        }

    analyze_calls: list[dict] = []

    async def fake_analyze_document(
        content: str,
        filename: str = "",
        format_hint: str = "",
        has_structured_rows: bool = False,
        recipe_config: dict | None = None,
        image_bytes: bytes | None = None,
        fallback_patterns: dict | None = None,
        canonical_fields: dict | None = None,
        prompt_config: dict | None = None,
    ):
        del (
            content,
            filename,
            format_hint,
            has_structured_rows,
            image_bytes,
            fallback_patterns,
            canonical_fields,
            prompt_config,
        )
        recipe_config = recipe_config or {}
        analyze_calls.append(recipe_config)
        if recipe_config.get("field_descriptions"):
            return {
                "doc_type": "INVOICE",
                "confidence": 0.96,
                "reasoning": "reused learned snapshot",
                "fields": {
                    "currency": "USD",
                    "payment_method": "Transferencia bancaria",
                    "total_amount": 2145.0,
                },
                "model_used": "learned-model",
                "prompt_sent": "rerun",
                "raw_response": "{}",
            }
        return {
            "doc_type": "INVOICE",
            "confidence": 0.90,
            "reasoning": "initial zero-shot pass",
            "fields": {
                "currency": "PEN",
                "total_amount": 2145.0,
            },
            "model_used": "base-model",
            "prompt_sent": "initial",
            "raw_response": "{}",
        }

    import app.config.database as _db_mod

    monkeypatch.setattr(_db_mod, "SessionLocal", _SessionFactory(db))
    monkeypatch.setattr(
        "app.modules.importador.ocr_service.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.analyze_document",
        fake_analyze_document,
    )

    asyncio.run(
        _run_processing(
            document.id,
            tenant_id,
            "tester",
            b"%PDF-1.4 fake",
            "factura-aprendizaje.pdf",
            "PDF",
            None,
            False,
        )
    )

    db.expire_all()
    stored = db.get(ImpDocumento, document.id)
    assert stored is not None
    assert stored.recipe_snapshot_id is not None
    assert stored.llm_model == "learned-model"
    assert stored.datos_extraidos is not None
    assert stored.datos_extraidos["payment_method"] == "Transferencia bancaria"
    assert len(analyze_calls) == 2
    assert analyze_calls[0] == {}
    assert "field_descriptions" in analyze_calls[1]
    assert "Learning from confirmed similar documents:" in str(analyze_calls[1].get("prompt_user"))
