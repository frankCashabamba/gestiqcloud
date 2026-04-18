import asyncio
import os
import zipfile
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import inspect, text

os.environ["DEBUG"] = "0"

from app.config.database import Base
from app.models.importador import (
    IcuRecipe,
    IcuRecipeDraft,
    IcuRecipeSnapshot,
    ImpBatchImport,
    ImpBatchItem,
    ImpDocumento,
)
from app.modules.importador import tasks
from app.modules.importador.batch_service import enqueue_async_batch


def test_enqueue_async_batch_auto_creates_missing_tracking_tables(db, tenant_minimal, monkeypatch):
    engine = db.get_bind()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            IcuRecipe.__table__,
            IcuRecipeDraft.__table__,
            IcuRecipeSnapshot.__table__,
            ImpDocumento.__table__,
        ],
    )
    db.execute(text("DROP TABLE IF EXISTS imp_batch_item"))
    db.execute(text("DROP TABLE IF EXISTS imp_batch_import"))
    db.commit()

    monkeypatch.setattr(tasks, "store_payload", lambda doc_id, file_bytes: None)
    monkeypatch.setattr(tasks, "process_document_task", None)

    upload = UploadFile(filename="factura.pdf", file=BytesIO(b"%PDF-1.4\nfake\n"))
    result = asyncio.run(
        enqueue_async_batch(
            files=[upload],
            tenant_id=tenant_minimal["tenant_id"],
            user_id="test-user",
            force=False,
            recipe_snapshot_id=None,
            db=db,
        )
    )

    inspector = inspect(engine)
    assert inspector.has_table("imp_batch_import")
    assert inspector.has_table("imp_batch_item")
    assert len(result) == 1
    assert result[0]["estado"] == "PENDING"
    assert db.query(ImpDocumento).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 1
    assert db.query(ImpBatchImport).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 1
    assert db.query(ImpBatchItem).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 1


def test_enqueue_async_batch_expands_zip_entries_before_queueing(db, tenant_minimal, monkeypatch):
    queued: list[dict] = []

    class FakeTask:
        @staticmethod
        def apply_async(*, kwargs, queue):
            queued.append({"kwargs": kwargs, "queue": queue})

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("ventas.csv", "fecha,total\n2026-04-01,12.5\n")
        zf.writestr("ticket.pdf", b"%PDF-1.4\nfake\n")

    monkeypatch.setattr(tasks, "store_payload", lambda doc_id, file_bytes: None)
    monkeypatch.setattr(tasks, "process_document_task", FakeTask())

    upload = UploadFile(filename="lote.zip", file=BytesIO(zip_buffer.getvalue()))
    result = asyncio.run(
        enqueue_async_batch(
            files=[upload],
            tenant_id=tenant_minimal["tenant_id"],
            user_id="test-user",
            force=False,
            recipe_snapshot_id=None,
            db=db,
        )
    )

    assert [item["nombre_archivo"] for item in result] == [
        "lote.zip::ventas.csv",
        "lote.zip::ticket.pdf",
    ]
    assert len(queued) == 2
    assert {item["kwargs"]["tipo_archivo"] for item in queued} == {"CSV", "PDF"}
    assert db.query(ImpDocumento).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 2
    assert db.query(ImpBatchItem).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 2


def test_enqueue_async_batch_reuses_same_hash_once_per_request(db, tenant_minimal, monkeypatch):
    queued: list[dict] = []

    class FakeTask:
        @staticmethod
        def apply_async(*, kwargs, queue):
            queued.append({"kwargs": kwargs, "queue": queue})

    monkeypatch.setattr(tasks, "store_payload", lambda doc_id, file_bytes: None)
    monkeypatch.setattr(tasks, "process_document_task", FakeTask())

    same_bytes = b"%PDF-1.4\nsame-doc\n"
    uploads = [
        UploadFile(filename="Stock-02-11-2025.pdf", file=BytesIO(same_bytes)),
        UploadFile(filename="Stock-04-12-2025.pdf", file=BytesIO(same_bytes)),
    ]

    result = asyncio.run(
        enqueue_async_batch(
            files=uploads,
            tenant_id=tenant_minimal["tenant_id"],
            user_id="test-user",
            force=False,
            recipe_snapshot_id=None,
            db=db,
        )
    )

    assert len(queued) == 1
    assert len(result) == 2
    assert result[0]["id"] == result[1]["id"]
    assert {item["action"] for item in result} == {"CREATED", "REUSED"}
    assert db.query(ImpDocumento).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 1
    assert db.query(ImpBatchItem).filter_by(tenant_id=tenant_minimal["tenant_id"]).count() == 2
