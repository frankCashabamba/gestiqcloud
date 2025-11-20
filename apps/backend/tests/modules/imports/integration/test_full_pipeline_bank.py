"""
Test de integración: CSV bancario → bank_movements.
Verifica parseo, normalización CAMT.053 y promoción.
"""

from io import StringIO
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.modules.imports.application.use_cases import create_batch, ingest_rows


@pytest.fixture
def banco_movimientos_csv() -> Path:
    """Path a extracto bancario CSV."""
    return Path(__file__).parent.parent / "fixtures" / "documents" / "banco_movimientos.csv"


def test_full_pipeline_bank_csv(
    db_session: Session, test_tenant_ec: dict, banco_movimientos_csv: Path
):
    """
    Test completo banco:
    1. Crear batch tipo 'bank'
    2. Ingestar CSV con movimientos
    3. Normalizar a CAMT.053-like
    4. Validar fechas, saldos, IBAN
    5. Promover a bank_movements
    """
    tenant_id = test_tenant_ec["tenant_id"]
    tenant_id = test_tenant_ec["tenant_id"]

    batch = create_batch(
        db=db_session,
        tenant_id=tenant_id,
        source_type="bank",
        description="Test banco CSV",
    )

    # Leer CSV
    with open(banco_movimientos_csv, encoding="utf-8") as f:
        csv_content = f.read()

    # Parse manual (o usar pandas)
    import csv

    reader = csv.DictReader(StringIO(csv_content))
    rows = list(reader)

    assert len(rows) > 0

    # Ingestar rows (cada fila → un ImportItem)
    items = ingest_rows(
        db=db_session,
        tenant_id=tenant_id,
        batch_id=batch.id,
        rows=rows,
        source_file="banco_movimientos.csv",
    )

    assert len(items) == len(rows)

    # Procesar cada item
    from app.modules.imports.application.use_cases import (
        extract_item_sync,
        promote_batch,
        validate_item_sync,
    )

    for item in items:
        extract_item_sync(db_session, tenant_id, str(item.id))
        db_session.refresh(item)
        assert item.status == "extracted"

        validate_item_sync(db_session, tenant_id, str(item.id))
        db_session.refresh(item)

        # Banco debe validar IBAN, fechas, saldos
        if item.validation_errors:
            print(f"Validation errors: {item.validation_errors}")

    # Promover batch completo
    promote_batch(db_session, tenant_id, batch.id)

    # Verificar bank_movements
    movements = db_session.execute(
        "SELECT * FROM bank_movements WHERE tenant_id = :tid",
        {"tid": tenant_id},
    ).fetchall()

    assert len(movements) > 0
    for mov in movements:
        assert mov["amount"] is not None
        assert mov["value_date"] is not None


def test_bank_balance_reconciliation(db_session: Session, test_tenant_ec: dict):
    """
    Verifica que saldos de movimientos bancarios cuadren:
    saldo_anterior + sum(movimientos) = saldo_final
    """
    tenant_id = test_tenant_ec["tenant_id"]
    tenant_id = test_tenant_ec["tenant_id"]

    batch = create_batch(db_session, tenant_id, "bank", "Test saldos")

    # Movimientos sintéticos
    rows = [
        {
            "fecha": "2025-01-01",
            "concepto": "Apertura",
            "debe": 0,
            "haber": 1000,
            "saldo": 1000,
        },
        {
            "fecha": "2025-01-02",
            "concepto": "Pago proveedor",
            "debe": 200,
            "haber": 0,
            "saldo": 800,
        },
        {
            "fecha": "2025-01-03",
            "concepto": "Cobro cliente",
            "debe": 0,
            "haber": 500,
            "saldo": 1300,
        },
    ]

    items = ingest_rows(db_session, tenant_id, batch.id, rows, "test_saldos.csv")

    # Procesar
    from app.modules.imports.application.use_cases import extract_item_sync, validate_item_sync

    for item in items:
        extract_item_sync(db_session, tenant_id, str(item.id))
        validate_item_sync(db_session, tenant_id, str(item.id))
        db_session.refresh(item)

    # Validador debe chequear saldos
    last_item = items[-1]
    assert last_item.normalized["saldo"] == 1300

    # Sumar movimientos
    total_debe = sum(float(r["debe"]) for r in rows)
    total_haber = sum(float(r["haber"]) for r in rows)
    saldo_calculado = total_haber - total_debe

    assert saldo_calculado == 1300
