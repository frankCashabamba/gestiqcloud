from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import text as sa_text

from app.config.database import Base
from app.models.importador import (
    ImpBatchImport,
    ImpBatchItem,
    ImpDocumento,
    ImpVendorSnapshot,
    IcuRecipe,
    IcuRecipeDraft,
    IcuRecipeSnapshot,
)
from app.modules.importador.router import purge_all_importador, purge_full_importador


def _create_learning_aux_tables(db) -> None:
    db.execute(
        sa_text(
            """
            CREATE TABLE IF NOT EXISTS imp_field_alias (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NULL,
                canonical_field TEXT NOT NULL,
                alias TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT 'learned',
                confirmed_count INTEGER NOT NULL DEFAULT 0,
                last_seen_at TEXT NULL,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
    )
    db.execute(
        sa_text(
            """
            CREATE TABLE IF NOT EXISTS imp_documento_successor (
                predecessor_id TEXT NOT NULL,
                successor_id TEXT NOT NULL,
                reason TEXT NULL,
                UNIQUE(predecessor_id, successor_id)
            )
            """
        )
    )
    db.commit()


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
    _create_learning_aux_tables(db)

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


def test_purge_all_importador_preserves_learning_memory(db, tenant_minimal):
    engine = db.get_bind()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ImpDocumento.__table__,
            ImpBatchImport.__table__,
            ImpBatchItem.__table__,
            IcuRecipe.__table__,
            IcuRecipeDraft.__table__,
            IcuRecipeSnapshot.__table__,
            ImpVendorSnapshot.__table__,
        ],
    )
    _create_learning_aux_tables(db)

    tenant_id = tenant_minimal["tenant_id"]
    documento = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=1024,
        estado="REVIEW",
    )
    recipe = IcuRecipe(
        tenant_id=tenant_id,
        name="Receta test",
    )
    db.add_all([documento, recipe])
    db.flush()

    draft = IcuRecipeDraft(
        tenant_id=tenant_id,
        recipe_id=recipe.id,
        prompt_user="prompt",
    )
    db.add(draft)
    db.flush()

    snapshot = IcuRecipeSnapshot(
        tenant_id=tenant_id,
        recipe_id=recipe.id,
        draft_id=draft.id,
        content_json={"example": True},
    )
    db.add(snapshot)
    db.flush()

    vendor_snapshot = ImpVendorSnapshot(
        tenant_id=tenant_id,
        ruc="20123456789",
        vendor_norm="proveedor test",
        recipe_snapshot_id=snapshot.id,
    )
    db.add(vendor_snapshot)
    db.execute(
        sa_text(
            "INSERT INTO imp_field_alias "
            "(id, tenant_id, canonical_field, alias, priority, source, confirmed_count, active) "
            "VALUES (:id, :tenant_id, :canonical_field, :alias, 5, 'learned', 1, 1)"
        ),
        {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "canonical_field": "supplier_ref",
            "alias": "ref proveedor",
        },
    )
    db.execute(
        sa_text(
            "INSERT INTO imp_documento_successor (predecessor_id, successor_id, reason) "
            "VALUES (:predecessor_id, :successor_id, :reason)"
        ),
        {
            "predecessor_id": str(documento.id),
            "successor_id": str(documento.id),
            "reason": "same_name_new_hash",
        },
    )
    db.commit()

    request = SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(tenant_id)}))

    result = purge_all_importador(request, db)

    assert result["tables"]["imp_documento"] == 1
    assert db.query(ImpDocumento).filter(ImpDocumento.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchImport).filter(ImpBatchImport.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchItem).filter(ImpBatchItem.tenant_id == tenant_id).count() == 0
    assert db.query(IcuRecipe).filter(IcuRecipe.tenant_id == tenant_id).count() == 1
    assert db.query(IcuRecipeDraft).filter(IcuRecipeDraft.tenant_id == tenant_id).count() == 1
    assert db.query(IcuRecipeSnapshot).filter(IcuRecipeSnapshot.tenant_id == tenant_id).count() == 1
    assert db.query(ImpVendorSnapshot).filter(ImpVendorSnapshot.tenant_id == tenant_id).count() == 1
    alias_count = db.execute(
        sa_text("SELECT COUNT(*) FROM imp_field_alias WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    ).scalar_one()
    successor_count = db.execute(sa_text("SELECT COUNT(*) FROM imp_documento_successor")).scalar_one()
    assert alias_count == 1
    assert successor_count == 0


def test_purge_full_importador_removes_learning_memory(db, tenant_minimal):
    engine = db.get_bind()
    Base.metadata.create_all(
        bind=engine,
        tables=[
            ImpDocumento.__table__,
            ImpBatchImport.__table__,
            ImpBatchItem.__table__,
            IcuRecipe.__table__,
            IcuRecipeDraft.__table__,
            IcuRecipeSnapshot.__table__,
            ImpVendorSnapshot.__table__,
        ],
    )
    _create_learning_aux_tables(db)

    tenant_id = tenant_minimal["tenant_id"]
    documento = ImpDocumento(
        tenant_id=tenant_id,
        nombre_archivo="factura.pdf",
        tipo_archivo="PDF",
        tamanio_bytes=1024,
        estado="REVIEW",
    )
    recipe = IcuRecipe(
        tenant_id=tenant_id,
        name="Receta test",
    )
    db.add_all([documento, recipe])
    db.flush()

    draft = IcuRecipeDraft(
        tenant_id=tenant_id,
        recipe_id=recipe.id,
        prompt_user="prompt",
    )
    db.add(draft)
    db.flush()

    snapshot = IcuRecipeSnapshot(
        tenant_id=tenant_id,
        recipe_id=recipe.id,
        draft_id=draft.id,
        content_json={"example": True},
    )
    db.add(snapshot)
    db.flush()

    vendor_snapshot = ImpVendorSnapshot(
        tenant_id=tenant_id,
        ruc="20123456789",
        vendor_norm="proveedor test",
        recipe_snapshot_id=snapshot.id,
    )
    db.add(vendor_snapshot)
    db.execute(
        sa_text(
            "INSERT INTO imp_field_alias "
            "(id, tenant_id, canonical_field, alias, priority, source, confirmed_count, active) "
            "VALUES (:id, :tenant_id, :canonical_field, :alias, 5, 'learned', 1, 1)"
        ),
        {
            "id": str(uuid4()),
            "tenant_id": str(tenant_id),
            "canonical_field": "supplier_ref",
            "alias": "ref proveedor",
        },
    )
    db.execute(
        sa_text(
            "INSERT INTO imp_documento_successor (predecessor_id, successor_id, reason) "
            "VALUES (:predecessor_id, :successor_id, :reason)"
        ),
        {
            "predecessor_id": str(documento.id),
            "successor_id": str(documento.id),
            "reason": "same_name_new_hash",
        },
    )
    db.commit()

    request = SimpleNamespace(state=SimpleNamespace(access_claims={"tenant_id": str(tenant_id)}))

    result = purge_full_importador(request, db)

    assert result["tables"]["imp_documento"] == 1
    assert db.query(ImpDocumento).filter(ImpDocumento.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchImport).filter(ImpBatchImport.tenant_id == tenant_id).count() == 0
    assert db.query(ImpBatchItem).filter(ImpBatchItem.tenant_id == tenant_id).count() == 0
    assert db.query(IcuRecipe).filter(IcuRecipe.tenant_id == tenant_id).count() == 0
    assert db.query(IcuRecipeDraft).filter(IcuRecipeDraft.tenant_id == tenant_id).count() == 0
    assert db.query(IcuRecipeSnapshot).filter(IcuRecipeSnapshot.tenant_id == tenant_id).count() == 0
    assert db.query(ImpVendorSnapshot).filter(ImpVendorSnapshot.tenant_id == tenant_id).count() == 0
    alias_count = db.execute(
        sa_text("SELECT COUNT(*) FROM imp_field_alias WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    ).scalar_one()
    successor_count = db.execute(sa_text("SELECT COUNT(*) FROM imp_documento_successor")).scalar_one()
    assert alias_count == 0
    assert successor_count == 0
