"""
Endpoints de conversión de documentos para módulo POS.

Permite convertir recibos POS en facturas formales (caso B2B).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.shared.services import DocumentConverter

router = APIRouter(
    prefix="/pos/receipts",
    tags=["POS - Conversions"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_uuid(request: Request) -> UUID:
    try:
        return UUID(str(request.state.access_claims.get("tenant_id")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


class InvoiceFromReceiptRequest(BaseModel):
    """Request para crear factura formal desde recibo POS"""

    customer_id: str = Field(..., description="ID del cliente con datos fiscales completos")
    notes: str | None = Field(None, description="Notas adicionales para la factura")


class InvoiceFromReceiptResponse(BaseModel):
    """Response de creación de factura desde recibo POS"""

    invoice_id: str
    receipt_id: str
    invoice_number: str
    status: str
    message: str


@router.post("/{receipt_id}/invoice", response_model=InvoiceFromReceiptResponse, status_code=201)
def create_invoice_from_pos_receipt(
    receipt_id: str,
    payload: InvoiceFromReceiptRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Convierte un recibo POS pagado en factura formal.

    Caso de uso típico:
    1. Cliente compra en tienda física (POS)
    2. Se genera recibo con pago inmediato
    3. Cliente solicita factura formal con datos fiscales
    4. Se crea factura vinculada al recibo

    Requisitos:
    - El recibo debe estar en estado 'paid'
    - El recibo no debe tener ya una factura asociada
    - El cliente debe existir y tener datos fiscales completos

    Proceso:
    1. Valida el recibo POS
    2. Valida los datos fiscales del cliente
    3. Crea la factura con número automático
    4. Copia las líneas del recibo
    5. Vincula recibo ↔ factura
    6. Marca recibo como 'invoiced'

    Ejemplo:
        POST /api/v1/tenant/pos/receipts/uuid-del-recibo/invoice
        {
            "customer_id": "uuid-del-cliente",
            "notes": "Factura solicitada por cliente empresarial"
        }

    Returns:
        {
            "invoice_id": "uuid-de-la-factura",
            "receipt_id": "uuid-del-recibo",
            "invoice_number": "A-2024-000456",
            "status": "created",
            "message": "Factura A-2024-000456 creada desde recibo R-0123"
        }
    """
    tenant_id = _tenant_uuid(request)

    # Validar UUIDs
    try:
        receipt_uuid = UUID(receipt_id)
        customer_uuid = UUID(payload.customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="receipt_id o customer_id no son UUIDs válidos")

    # Verificar que el cliente existe y tiene datos fiscales
    from sqlalchemy import text

    customer = db.execute(
        text(
            """
            SELECT id, name, identificacion, email
            FROM clients
            WHERE id = :cid AND tenant_id = :tid
        """
        ),
        {"cid": customer_uuid, "tid": str(tenant_id)},
    ).first()

    if not customer:
        raise HTTPException(status_code=404, detail=f"Cliente {payload.customer_id} no encontrado")

    if not customer[2]:  # identificacion
        raise HTTPException(
            status_code=400, detail="El cliente debe tener número de identificación fiscal"
        )

    converter = DocumentConverter(db)

    try:
        # Preparar datos adicionales
        invoice_data = {}
        if payload.notes:
            invoice_data["notes"] = payload.notes

        # Convertir recibo a factura
        invoice_id = converter.pos_receipt_to_invoice(
            receipt_id=receipt_uuid,
            tenant_id=tenant_id,
            customer_id=customer_uuid,
            invoice_data=invoice_data if invoice_data else None,
        )

        # Obtener número de factura y recibo generados
        invoice_number = db.execute(
            text("SELECT numero FROM invoices WHERE id = :id"), {"id": invoice_id}
        ).scalar()

        receipt_number = db.execute(
            text("SELECT number FROM pos_receipts WHERE id = :id"), {"id": receipt_uuid}
        ).scalar()

        return InvoiceFromReceiptResponse(
            invoice_id=str(invoice_id),
            receipt_id=str(receipt_uuid),
            invoice_number=invoice_number,
            status="created",
            message=f"Factura {invoice_number} creada exitosamente desde recibo {receipt_number}",
        )

    except ValueError as e:
        # Errores de validación (recibo no existe, ya facturado, etc.)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Errores inesperados
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al crear factura desde recibo: {str(e)}"
        )


@router.get("/{receipt_id}/invoice")
def get_invoice_from_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Obtiene la factura asociada a un recibo POS.

    Returns:
        {
            "invoice_id": "uuid",
            "invoice_number": "A-2024-000456",
            "receipt_id": "uuid",
            "receipt_number": "R-0123",
            "created_at": "2024-01-15T14:30:00"
        }

    Returns 404 si el recibo no tiene factura.
    """
    tenant_id = _tenant_uuid(request)

    try:
        receipt_uuid = UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="receipt_id no es un UUID válido")

    from sqlalchemy import text

    # Buscar recibo y su factura
    result = db.execute(
        text(
            """
            SELECT
                r.id::text as receipt_id,
                r.number as receipt_number,
                i.id::text as invoice_id,
                i.numero as invoice_number,
                i.fecha_creacion
            FROM pos_receipts r
            LEFT JOIN invoices i ON i.id = r.invoice_id
            WHERE r.id = :rid AND r.tenant_id = :tid
        """
        ),
        {"rid": receipt_uuid, "tid": str(tenant_id)},
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail=f"Recibo {receipt_id} no encontrado")

    if not result[2]:  # invoice_id
        raise HTTPException(
            status_code=404, detail=f"El recibo {result[1]} no tiene factura asociada"
        )

    return {
        "receipt_id": result[0],
        "receipt_number": result[1],
        "invoice_id": result[2],
        "invoice_number": result[3],
        "created_at": result[4].isoformat() if result[4] else None,
    }


@router.delete("/{receipt_id}/invoice")
def unlink_invoice_from_receipt(receipt_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Desvincula una factura de un recibo POS (solo si está en borrador).

    ADVERTENCIA: Solo para corrección de errores administrativos.
    No elimina la factura, solo rompe el vínculo.

    Returns 403 si la factura ya está emitida/pagada.
    """
    tenant_id = _tenant_uuid(request)

    try:
        receipt_uuid = UUID(receipt_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="receipt_id no es un UUID válido")

    from sqlalchemy import text

    # Verificar estado de la factura
    result = db.execute(
        text(
            """
            SELECT i.estado
            FROM pos_receipts r
            JOIN invoices i ON i.id = r.invoice_id
            WHERE r.id = :rid AND r.tenant_id = :tid
        """
        ),
        {"rid": receipt_uuid, "tid": str(tenant_id)},
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail="Recibo no encontrado o sin factura vinculada")

    if result[0] != "draft":
        raise HTTPException(
            status_code=403,
            detail=f"No se puede desvincular una factura en estado '{result[0]}'. Solo facturas en borrador.",
        )

    # Desvincular
    db.execute(
        text(
            """
            UPDATE pos_receipts
            SET invoice_id = NULL, status = 'paid'
            WHERE id = :rid AND tenant_id = :tid
        """
        ),
        {"rid": receipt_uuid, "tid": str(tenant_id)},
    )

    db.commit()

    return {
        "status": "unlinked",
        "message": "Factura desvinculada exitosamente. El recibo vuelve a estado 'paid'.",
    }
