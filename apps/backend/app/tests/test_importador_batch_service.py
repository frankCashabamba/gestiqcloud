import asyncio
import os
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
