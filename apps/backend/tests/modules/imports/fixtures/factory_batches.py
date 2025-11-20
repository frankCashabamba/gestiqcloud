"""
Factory para crear batches e items de prueba.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.core.modelsimport import ImportBatch, ImportItem


def create_test_batch(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    source_type: str = "invoices",
    description: str = "Test batch",
) -> ImportBatch:
    """Crea un batch de prueba."""
    batch = ImportBatch(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        source_type=source_type,
        description=description,
        status="draft",
        created_at=datetime.utcnow(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def create_test_item(
    db: Session,
    *,
    batch_id: uuid.UUID,
    tenant_id: uuid.UUID,
    filename: str = "test.pdf",
    file_key: str = None,
    file_sha256: str = None,
    status: str = "preprocessing",
    normalized: dict[str, Any] = None,
) -> ImportItem:
    """Crea un item de prueba."""
    if file_key is None:
        file_key = f"imports/{tenant_id}/{batch_id}/{filename}"

    if file_sha256 is None:
        file_sha256 = f"sha256_{uuid.uuid4().hex[:16]}"

    item = ImportItem(
        id=uuid.uuid4(),
        batch_id=batch_id,
        tenant_id=tenant_id,
        filename=filename,
        file_key=file_key,
        file_size=1024,
        file_sha256=file_sha256,
        status=status,
        normalized=normalized,
        created_at=datetime.utcnow(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_mock_invoice_normalized() -> dict[str, Any]:
    """Devuelve normalized mock de factura válida."""
    return {
        "proveedor": {
            "tax_id": "1790016919001",
            "nombre": "Proveedor Test S.A.",
            "direccion": "Av. Test 123",
        },
        "cliente": {
            "tax_id": "0992345678001",
            "nombre": "Cliente Test",
        },
        "totales": {
            "subtotal": 100.00,
            "iva": 12.00,
            "total": 112.00,
        },
        "lineas": [
            {
                "descripcion": "Producto A",
                "cantidad": 1,
                "precio_unitario": 100.00,
                "subtotal": 100.00,
            }
        ],
        "fecha_emision": "2025-01-15",
        "numero_factura": "001-001-000001234",
    }


def create_mock_bank_normalized() -> dict[str, Any]:
    """Devuelve normalized mock de movimiento bancario."""
    return {
        "cuenta_iban": "EC12345678901234567890",
        "fecha_valor": "2025-01-15",
        "concepto": "Transferencia recibida",
        "importe": 500.00,
        "saldo": 1500.00,
        "referencia": "REF123456",
    }


def create_items_batch(
    db: Session,
    *,
    batch: ImportBatch,
    count: int = 5,
    status: str = "extracted",
    normalized_factory=create_mock_invoice_normalized,
) -> list[ImportItem]:
    """Crea múltiples items para un batch."""
    items = []
    for i in range(count):
        item = create_test_item(
            db,
            batch_id=batch.id,
            tenant_id=batch.tenant_id,
            filename=f"test_{i}.pdf",
            status=status,
            normalized=normalized_factory(),
        )
        items.append(item)
    return items
