from __future__ import annotations

import asyncio
import hashlib
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from app.models.importador import IcuRecipeSnapshot, ImpDocumento
from app.modules.importador import crud
from app.modules.importador.auto_recipe import resolve_auto_recipe_from_text
from app.modules.importador.batch_service import enqueue_async_batch
from app.modules.importador.router import _learn_from_confirmation, upload_files


def _fake_request(tenant_id) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={"tenant_id": str(tenant_id), "user_id": "tester"},
        )
    )


def test_learn_from_confirmation_bumps_learning_version(db: Session, tenant_minimal):
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

    document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-confirmacion.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        recipe_snapshot_id=snapshot_id,
        datos_extraidos={"currency": "PEN", "total_amount": 2145.0},
    )
    db.add(document)
    db.commit()

    _learn_from_confirmation(
        db,
        document,
        {"currency": "PEN", "total_amount": 2145.0, "payment_method": "Transferencia bancaria"},
        "tester",
    )
    db.commit()

    snapshot = db.get(IcuRecipeSnapshot, snapshot_id)
    assert snapshot is not None
    assert snapshot.content_json["learned_field_descriptions"]["payment_method"].startswith(
        "Users corrected"
    )
    assert snapshot.content_json["field_learning_memory"]["payment_method"]["corrected_count"] == 1
    assert snapshot.content_json["learning_prompt_user"].startswith(
        "Learning from confirmed similar documents:"
    )
    assert snapshot.content_json["learning_version"] == 1
    assert snapshot.content_json["learning_updated_at"]


def test_learn_from_confirmation_accumulates_snapshot_memory(db: Session, tenant_minimal):
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

    first_document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-1.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        recipe_snapshot_id=snapshot_id,
        datos_extraidos={"payment_method": "credito"},
    )
    second_document = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-2.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=128,
        estado="REVIEW",
        recipe_snapshot_id=snapshot_id,
        datos_extraidos={"payment_method": "contado"},
    )
    db.add_all([first_document, second_document])
    db.commit()

    _learn_from_confirmation(
        db,
        first_document,
        {"payment_method": "Transferencia bancaria"},
        "tester",
    )
    _learn_from_confirmation(
        db,
        second_document,
        {"payment_method": "Deposito"},
        "tester",
    )
    db.commit()

    snapshot = db.get(IcuRecipeSnapshot, snapshot_id)
    assert snapshot is not None
    memory = snapshot.content_json["field_learning_memory"]["payment_method"]
    assert memory["confirmed_count"] == 2
    assert memory["corrected_count"] == 2
    assert memory["confirmed_examples"][:2] == ["Deposito", "Transferencia bancaria"]
    assert "Recent examples" in snapshot.content_json["learning_prompt_user"]


def test_upload_files_reuses_text_snapshot_learning_and_persists_canonical_document(
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
        "payment_method": "Recent confirmed example: Transferencia bancaria. Extract the exact printed payment method when visible."
    }
    content["learning_version"] = 2
    snapshot.content_json = content
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
                "confidence": 0.97,
                "reasoning": "reused learned snapshot",
                "fields": {
                    "currency": "PEN",
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

    monkeypatch.setattr(
        "app.modules.importador.router.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.modules.importador.router.analyze_document",
        fake_analyze_document,
    )

    upload = UploadFile(BytesIO(b"%PDF-1.4 fake"), filename="factura-aprendizaje-upload.pdf")
    request = _fake_request(tenant_id)

    result = asyncio.run(upload_files(request=request, files=[upload], force=False, db=db))

    assert len(result) == 1
    stored = db.get(ImpDocumento, result[0].id)
    assert stored is not None
    assert stored.recipe_snapshot_id is not None
    assert stored.llm_model == "learned-model"
    assert stored.datos_extraidos is not None
    assert stored.datos_extraidos["payment_method"] == "Transferencia bancaria"
    assert stored.raw_ai_json["run"]["learning_version_applied"] == 2
    assert (
        stored.raw_ai_json["canonical_document"]["extensions"]["payment_method"]
        == "Transferencia bancaria"
    )
    assert len(analyze_calls) == 2
    assert analyze_calls[0] == {}
    assert "field_descriptions" in analyze_calls[1]
    assert "Learning from confirmed similar documents:" in str(analyze_calls[1].get("prompt_user"))


def test_enqueue_async_batch_bootstraps_learning_and_reuses_same_hash_document(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    file_bytes = b"%PDF-1.4 duplicate"
    filename = "factura-duplicada.pdf"
    file_hash = hashlib.sha256(file_bytes).hexdigest()

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
    assert snapshot.content_json.get("learning_version") is None

    existing = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo=filename,
        tipo_archivo="PDF",
        tamanio_bytes=len(file_bytes),
        hash_sha256=file_hash,
        estado="REVIEW",
        usuario_id="tester",
        recipe_snapshot_id=snapshot_id,
        datos_extraidos={"currency": "PEN", "total_amount": 2145.0, "payment_method": "credito"},
        datos_confirmados={
            "currency": "PEN",
            "total_amount": 2145.0,
            "payment_method": "credito",
        },
        raw_ai_json={"run": {"learning_version_applied": 0}},
    )
    db.add(existing)
    db.commit()

    class _DummyTask:
        def delay(self, **kwargs):
            return kwargs

    monkeypatch.setattr("app.modules.importador.tasks.store_payload", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.modules.importador.tasks.process_document_task", _DummyTask())
    monkeypatch.setattr(
        "app.modules.importador.batch_service._ensure_batch_tracking_storage",
        lambda _db: True,
    )

    upload = UploadFile(BytesIO(file_bytes), filename=filename)

    result = asyncio.run(
        enqueue_async_batch(
            files=[upload],
            tenant_id=tenant_id,
            user_id=str(uuid4()),
            force=False,
            recipe_snapshot_id=None,
            db=db,
        )
    )

    assert len(result) == 1
    assert str(result[0]["id"]) == str(existing.id)
    assert result[0]["action"] == "REUSED"
    assert "reutilizo el mismo registro" in result[0]["message"]
    all_docs = db.query(ImpDocumento).filter(ImpDocumento.nombre_archivo == filename).all()
    assert len(all_docs) == 1
    db.refresh(existing)
    assert any(log.accion == "SKIP_DUPLICATE" for log in existing.logs)
    db.refresh(snapshot)
    assert snapshot.content_json["learning_version"] == 1
    assert "payment_method" in (snapshot.content_json.get("field_descriptions") or {})


def test_upload_files_links_same_name_new_hash_as_successor(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS imp_documento_successor (
                predecessor_id TEXT NOT NULL,
                successor_id TEXT NOT NULL,
                reason TEXT,
                UNIQUE(predecessor_id, successor_id)
            )
            """
        )
    )
    db.commit()

    existing = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura-versionada.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=120,
        hash_sha256=hashlib.sha256(b"%PDF-1.4 old").hexdigest(),
        estado="CONFIRMED",
        usuario_id="tester",
        datos_confirmados={"currency": "PEN", "total_amount": 100.0},
    )
    db.add(existing)
    db.commit()

    async def fake_extract_text_from_file(_file_bytes: bytes, _filename: str):
        return {
            "text": "Factura nueva",
            "structured_data": None,
            "format": "PDF",
        }

    async def fake_analyze_document(*_args, **_kwargs):
        return {
            "doc_type": "INVOICE",
            "confidence": 0.95,
            "reasoning": "test",
            "fields": {"currency": "PEN", "total_amount": 150.0},
            "model_used": "test-model",
            "prompt_sent": "test",
            "raw_response": "{}",
        }

    monkeypatch.setattr(
        "app.modules.importador.router.extract_text_from_file",
        fake_extract_text_from_file,
    )
    monkeypatch.setattr(
        "app.modules.importador.router.analyze_document",
        fake_analyze_document,
    )

    upload = UploadFile(BytesIO(b"%PDF-1.4 new"), filename="factura-versionada.pdf")
    result = asyncio.run(
        upload_files(
            request=_fake_request(tenant_id),
            files=[upload],
            force=False,
            db=db,
        )
    )

    assert len(result) == 1
    assert str(result[0].id) != str(existing.id)
    link = db.execute(
        text(
            """
            SELECT predecessor_id, successor_id, reason
            FROM imp_documento_successor
            WHERE predecessor_id = :predecessor_id
            """
        ),
        {"predecessor_id": str(existing.id)},
    ).first()
    assert link is not None
    assert str(link.successor_id) == str(result[0].id)
    assert link.reason == "same_name_new_hash"
    lineage = crud.list_documento_versions(db, result[0].id)
    assert len(lineage) == 1
    assert str(lineage[0]["id"]) == str(existing.id)
    assert lineage[0]["relation_direction"] == "predecessor"


def test_enqueue_async_batch_force_reprocesses_same_hash_without_creating_duplicate(
    db: Session, tenant_minimal, monkeypatch
):
    tenant_id = tenant_minimal["tenant_id"]
    file_bytes = b"%PDF-1.4 confirmed"
    filename = "factura-confirmada.pdf"
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    existing = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo=filename,
        tipo_archivo="PDF",
        tamanio_bytes=len(file_bytes),
        hash_sha256=file_hash,
        estado="CONFIRMED",
        usuario_id="tester",
        datos_extraidos={"currency": "PEN", "total_amount": 2145.0},
        datos_confirmados={"currency": "PEN", "total_amount": 2145.0},
        raw_ai_json={"run": {"learning_version_applied": 1}},
    )
    db.add(existing)
    db.commit()

    class _DummyTask:
        def delay(self, **kwargs):
            return kwargs

    monkeypatch.setattr("app.modules.importador.tasks.store_payload", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.modules.importador.tasks.process_document_task", _DummyTask())
    monkeypatch.setattr(
        "app.modules.importador.batch_service._ensure_batch_tracking_storage",
        lambda _db: True,
    )

    upload = UploadFile(BytesIO(file_bytes), filename=filename)

    result = asyncio.run(
        enqueue_async_batch(
            files=[upload],
            tenant_id=tenant_id,
            user_id=str(uuid4()),
            force=True,
            recipe_snapshot_id=None,
            db=db,
        )
    )

    db.refresh(existing)
    assert len(result) == 1
    assert str(result[0]["id"]) == str(existing.id)
    assert result[0]["action"] == "REPROCESS"
    assert "reproceso el mismo documento" in result[0]["message"]
    assert existing.estado == "PENDING"
    assert existing.datos_confirmados is None
    assert db.query(ImpDocumento).filter(ImpDocumento.nombre_archivo == filename).count() == 1
