from types import SimpleNamespace
from uuid import uuid4

from app.config.database import Base
from app.models.importador import ImpBatchImport, ImpBatchItem, ImpDocumento
from app.modules.importador.router import purge_all_importador


def test_purge_all_importador_removes_batches_and_items(db, tenant_minimal):
    engine = db.get_bind()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ImpDocumento.__table__,
            ImpBatchImport.__table__,
            ImpBatchItem.__table__,
        ],
    )

    tenant_id = tenant_minimal["tenant_id"]
    documento = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=1024,
        estado="REVIEW",
    )
    db.add(documento)
    db.flush()

    batch = ImpBatchImport(
        tenant_id=tenant_id,
        estado="PROCESSING",
        total_items=1,
    )
    db.add(batch)
    db.flush()

    batch_item = ImpBatchItem(
        id=uuid4(),
        tenant_id=tenant_id,
        batch_id=batch.id,
        documento_id=documento.id,
        nombre_archivo=documento.nombre_archivo,
        tamanio_bytes=documento.tamanio_bytes,
        orden=0,
        estado="PROCESSING",
    )
    db.add(batch_item)
    db.commit()

    request = SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(tenant_id)}))

    result = purge_all_importador(request, db)

    assert result["tables"]["imp_documento"] == 1
    assert result["tables"]["imp_batch_item"] == 1
    assert result["tables"]["imp_batch_import"] == 1
    assert db.query(ImpDocumento).filter(ImpDocumento.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchItem).filter(ImpBatchItem.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchImport).filter(ImpBatchImport.tenant_id == tenant_id).count() == 0
