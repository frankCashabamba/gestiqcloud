"""
Endpoints de conversión de documentos para módulo de ventas.

Permite convertir documentos entre tipos:
- SalesOrder → Invoice
- Quote → SalesOrder (futuro)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.shared.services import DocumentConverter

router = APIRouter(
    prefix="/sales_orders",
    tags=["Sales - Conversions"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_uuid(request: Request) -> UUID:
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


class InvoiceFromOrderRequest(BaseModel):
    """Request para crear factura desde orden de venta"""

    payment_terms: str | None = None
    notes: str | None = None


class InvoiceFromOrderResponse(BaseModel):
    """Response de creación de factura"""

    invoice_id: str
    order_id: int
    status: str
    message: str


@router.post("/{order_id}/invoice", response_model=InvoiceFromOrderResponse, status_code=201)
def create_invoice_from_sales_order(
    order_id: int,
    request: Request,
    payload: InvoiceFromOrderRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Convierte una orden de venta confirmada en factura.

    Requisitos:
    - La orden debe estar en estado 'confirmed' o 'delivered'
    - La orden no debe tener ya una factura asociada
    - La orden debe tener al menos un item

    Proceso:
    1. Valida la orden de venta
    2. Crea la factura con número automático
    3. Copia las líneas de la orden
    4. Marca la orden como 'invoiced'
    5. Mantiene relación bidireccional

    Ejemplo:
        POST /api/v1/tenant/sales_orders/123/invoice
        {
            "payment_terms": "30 days",
            "notes": "Cliente preferente"
        }

    Returns:
        {
            "invoice_id": "uuid-de-la-factura",
            "order_id": 123,
            "status": "created",
            "message": "Factura A-2024-000123 creada exitosamente"
        }
    """
    tenant_id = _tenant_uuid(request)

    converter = DocumentConverter(db)

    try:
        # Preparar datos adicionales si se enviaron
        invoice_data = {}
        if payload:
            if payload.payment_terms:
                invoice_data["payment_terms"] = payload.payment_terms
            if payload.notes:
                invoice_data["notes"] = payload.notes

        # Convertir orden a factura
        invoice_id = converter.sales_order_to_invoice(
            sales_order_id=order_id,
            tenant_id=tenant_id,
            invoice_data=invoice_data if invoice_data else None,
        )

        # Obtener número de factura generado
        from sqlalchemy import text

        numero = db.execute(
            text("SELECT numero FROM invoices WHERE id = :id"), {"id": invoice_id}
        ).scalar()

        return InvoiceFromOrderResponse(
            invoice_id=str(invoice_id),
            order_id=order_id,
            status="created",
            message=f"Factura {numero} creada exitosamente desde orden {order_id}",
        )

    except ValueError as e:
        # Errores de validación (orden no existe, ya facturada, etc.)
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Errores inesperados
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear factura desde orden: {str(e)}")


@router.get("/{order_id}/invoice")
def get_invoice_from_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    """
    Obtiene la factura asociada a una orden de venta.

    Returns:
        {
            "invoice_id": "uuid",
            "invoice_number": "A-2024-000123",
            "order_id": 123,
            "created_at": "2024-01-15T10:30:00"
        }

    Returns 404 si la orden no tiene factura.
    """
    tenant_id = _tenant_uuid(request)

    from sqlalchemy import text

    # Buscar factura vinculada a la orden
    result = db.execute(
        text("""
            SELECT id::text, numero, fecha_creacion
            FROM invoices
            WHERE metadata::jsonb->>'sales_order_id' = :order_id
            AND tenant_id = :tid
            LIMIT 1
        """),
        {"order_id": str(order_id), "tid": str(tenant_id)},
    ).first()

    if not result:
        raise HTTPException(
            status_code=404, detail=f"La orden {order_id} no tiene factura asociada"
        )

    return {
        "invoice_id": result[0],
        "invoice_number": result[1],
        "order_id": order_id,
        "created_at": result[2].isoformat() if result[2] else None,
    }


# Endpoint futuro para presupuestos
# @router.post("/quotes/{quote_id}/sales_order")
# def create_order_from_quote(...):
#     """Convierte presupuesto en orden de venta"""
#     pass
