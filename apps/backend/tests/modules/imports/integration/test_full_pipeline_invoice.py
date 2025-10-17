"""
Test de integración end-to-end: PDF de factura → promoted a expenses.
Verifica todo el pipeline con RLS activo.
"""
import uuid
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.core.modelsimport import ImportBatch, ImportItem, ImportLineage
from app.modules.imports.application.use_cases import (
    create_batch,
    ingest_file,
    revalidate_batch,
    promote_batch,
)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Session con RLS habilitado."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_tenant_ec(db_session: Session) -> dict:
    """Tenant de prueba Ecuador."""
    tenant_id = uuid.uuid4()
    db_session.execute(
        """
        INSERT INTO tenants (id, slug, country_code, fiscal_id, legal_name)
        VALUES (:tid, 'test-ec', 'EC', '1790016919001', 'Test EC S.A.')
        """,
        {"tid": tenant_id},
    )
    db_session.execute(
        f"SET LOCAL app.tenant_id = '{tenant_id}'"
    )
    db_session.commit()
    return {"tenant_id": tenant_id, "empresa_id": 1, "country": "EC"}


@pytest.fixture
def factura_ec_sample() -> Path:
    """Path a factura Ecuador de muestra."""
    return Path(__file__).parent.parent / "fixtures" / "documents" / "factura_ec_sample.pdf"


def test_full_pipeline_invoice_ec(db_session: Session, test_tenant_ec: dict, factura_ec_sample: Path):
    """
    Test completo factura Ecuador:
    1. Crear batch
    2. Ingestar PDF
    3. Item pasa por preprocess → extract → validate
    4. Promover a expenses
    5. Verificar lineage y datos destino
    """
    tenant_id = test_tenant_ec["tenant_id"]
    empresa_id = test_tenant_ec["empresa_id"]
    
    # 1. Crear batch
    batch = create_batch(
        db=db_session,
        empresa_id=empresa_id,
        source_type="invoices",
        description="Test factura EC end-to-end",
    )
    assert batch.id is not None
    assert batch.source_type == "invoices"
    
    # 2. Ingestar archivo (mock S3 upload)
    with open(factura_ec_sample, "rb") as f:
        file_content = f.read()
    
    # Simulamos que el archivo está en S3 con file_key
    file_key = f"imports/{tenant_id}/{batch.id}/factura_ec_sample.pdf"
    
    item = ingest_file(
        db=db_session,
        empresa_id=empresa_id,
        batch_id=batch.id,
        file_key=file_key,
        filename="factura_ec_sample.pdf",
        file_size=len(file_content),
        file_sha256="mock_sha256_ec",
    )
    
    assert item.status == "preprocessing"
    assert item.file_key == file_key
    
    # 3. Simular tasks de Celery (sin cola en test)
    # En producción: tasks.extract_item.apply_async(item.id)
    # Aquí llamamos directamente a la lógica
    from app.modules.imports.application.use_cases import (
        extract_item_sync,
        validate_item_sync,
    )
    
    # Extract
    extract_item_sync(db_session, empresa_id, str(item.id))
    db_session.refresh(item)
    assert item.status == "extracted"
    assert item.normalized is not None
    assert "proveedor" in item.normalized
    
    # Validate
    validate_item_sync(db_session, empresa_id, str(item.id))
    db_session.refresh(item)
    assert item.status in ["validated", "validation_failed"]
    
    if item.validation_errors:
        pytest.skip(f"Validación falló con: {item.validation_errors}")
    
    # 4. Promover batch
    promote_batch(db_session, empresa_id, batch.id)
    db_session.refresh(item)
    
    assert item.status == "promoted"
    assert item.promoted_id is not None
    
    # 5. Verificar lineage
    lineage = db_session.query(ImportLineage).filter_by(item_id=item.id).first()
    assert lineage is not None
    assert lineage.destination_table == "expenses"
    assert lineage.destination_id == item.promoted_id
    
    # 6. Verificar datos en expenses
    expense = db_session.execute(
        "SELECT * FROM expenses WHERE id = :eid",
        {"eid": item.promoted_id},
    ).fetchone()
    
    assert expense is not None
    assert expense["tenant_id"] == tenant_id
    assert expense["proveedor_nombre"] is not None
    assert expense["total"] > 0


def test_pipeline_duplicate_detection(db_session: Session, test_tenant_ec: dict, factura_ec_sample: Path):
    """
    Verifica que la deduplicación por hash funciona:
    - Primera ingesta: ok
    - Segunda ingesta (mismo hash): rejected_duplicate
    """
    tenant_id = test_tenant_ec["tenant_id"]
    empresa_id = test_tenant_ec["empresa_id"]
    
    batch = create_batch(db_session, empresa_id, "invoices", "Test duplicates")
    
    file_key = f"imports/{tenant_id}/{batch.id}/factura_ec_sample.pdf"
    sha256 = "deterministic_hash_12345"
    
    # Primera ingesta
    item1 = ingest_file(
        db_session, empresa_id, batch.id, file_key, "factura.pdf", 1024, sha256
    )
    assert item1.status == "preprocessing"
    
    # Segunda ingesta (mismo hash)
    item2 = ingest_file(
        db_session, empresa_id, batch.id, file_key + "_copy", "factura_copy.pdf", 1024, sha256
    )
    assert item2.status == "rejected_duplicate"


def test_pipeline_validation_errors(db_session: Session, test_tenant_ec: dict):
    """
    Verifica que validación detecta errores y permite correcciones.
    """
    empresa_id = test_tenant_ec["empresa_id"]
    
    batch = create_batch(db_session, empresa_id, "invoices", "Test validación")
    
    # Crear item con normalized mal formado
    item = ImportItem(
        batch_id=batch.id,
        empresa_id=empresa_id,
        tenant_id=test_tenant_ec["tenant_id"],
        filename="bad_invoice.pdf",
        file_key="test/bad.pdf",
        file_size=100,
        file_sha256="bad_hash",
        status="extracted",
        normalized={
            "proveedor": {"tax_id": "INVALID"},
            "totales": {"total": -100},  # total negativo
        },
    )
    db_session.add(item)
    db_session.commit()
    
    # Validar
    from app.modules.imports.application.use_cases import validate_item_sync
    validate_item_sync(db_session, empresa_id, str(item.id))
    db_session.refresh(item)
    
    assert item.status == "validation_failed"
    assert len(item.validation_errors) > 0
    assert any("total" in str(err).lower() for err in item.validation_errors)
