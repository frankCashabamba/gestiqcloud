"""
Endpoints de conversión de documentos para módulo de ventas.

Permite convertir documentos entre tipos:
- SalesOrder → Invoice
- SalesOrder → Checkout (factura + gasto de receta en una sola operación)
- Quote → SalesOrder (futuro)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.dependencies import get_tenant_uuid
from app.db.rls import ensure_rls
from app.models.expenses.expense import Expense
from app.models.recipes import Recipe
from app.models.sales.order import SalesOrder, SalesOrderItem
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
    tenant_id = get_tenant_uuid(request)

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
    tenant_id = get_tenant_uuid(request)

    from sqlalchemy import text

    # Buscar factura vinculada a la orden
    result = db.execute(
        text(
            """
            SELECT id::text, numero, fecha_creacion
            FROM invoices
            WHERE metadata::jsonb->>'sales_order_id' = :order_id
            AND tenant_id = :tid
            LIMIT 1
        """
        ),
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


# ---------------------------------------------------------------------------
# CHECKOUT: Factura + Gasto de receta en una sola operación
# ---------------------------------------------------------------------------

_UUID_REGEX = "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

# Estados que bloquean el checkout
_BLOCKED_STATUSES = {"cancelled", "invoiced"}


class CheckoutOrderRequest(BaseModel):
    """Parámetros opcionales para el cobro del pedido."""

    payment_method: str | None = None
    notes: str | None = None


class CheckoutOrderResponse(BaseModel):
    """Resultado del checkout."""

    invoice_id: str
    invoice_number: str
    order_id: str
    expenses_created: int
    expense_total: float
    status: str
    message: str
    expense_note: str | None = None


def _build_order_expense(
    db: Session,
    order: SalesOrder,
    items: list[SalesOrderItem],
    tenant_id: UUID,
    user_id: UUID,
    invoice_number: str,
    payment_method: str | None,
    notes_extra: str | None,
) -> tuple[Expense | None, float, str]:
    """
    Calcula el costo de receta para cada línea del pedido y crea un único
    Expense que agrupa todos los costos. Si ningún producto tiene receta,
    no se crea gasto y se devuelve (None, 0.0, motivo).

    Funciona para cualquier sector: panadería, taller, retail, etc.
    El product_id de cada línea se usa para buscar la receta activa.
    """
    import logging as _log
    _logger = _log.getLogger(__name__)

    ref = f"SALE-{order.number}"

    # Idempotencia: si ya existe el gasto no lo duplicamos
    existing = (
        db.query(Expense)
        .filter(Expense.tenant_id == tenant_id, Expense.invoice_number == ref)
        .first()
    )
    if existing:
        return existing, float(existing.total or 0), "ya existía"

    total_cost = Decimal("0")
    cost_lines: list[str] = []
    skip_reasons: list[str] = []

    for item in items:
        if not item.product_id:
            skip_reasons.append("línea sin producto")
            continue
        recipe: Recipe | None = (
            db.execute(
                select(Recipe).where(
                    Recipe.product_id == item.product_id,
                    Recipe.tenant_id == tenant_id,
                    Recipe.is_active.is_(True),
                )
            )
            .scalars()
            .first()
        )
        if recipe is None:
            skip_reasons.append(f"producto {item.product_id} sin receta activa")
            _logger.info("_build_order_expense: no hay receta activa para producto %s en tenant %s", item.product_id, tenant_id)
            continue

        unit_cost = Decimal(str(recipe.unit_cost or 0))
        if unit_cost <= 0:
            skip_reasons.append(f"receta '{recipe.name}' tiene unit_cost={unit_cost} (verifica ingredientes y costos)")
            _logger.info("_build_order_expense: receta '%s' tiene unit_cost=0, sin costo calculado", recipe.name)
            continue
        qty = Decimal(str(item.qty or 0))
        line_cost = unit_cost * qty
        total_cost += line_cost
        cost_lines.append(
            f"{recipe.name} × {qty} = {line_cost:.4f}"
        )

    if total_cost <= 0:
        reason = "; ".join(skip_reasons) if skip_reasons else "ningún producto con receta activa y costo > 0"
        _logger.info("_build_order_expense: no se genera gasto para orden %s — %s", order.number, reason)
        return None, 0.0, reason

    concept = f"Costo de venta - {order.number}"
    notes = (
        f"Auto-generado desde pedido {order.number}.\n"
        + "\n".join(cost_lines)
        + (f"\n{notes_extra}" if notes_extra else "")
    )

    expense = Expense(
        tenant_id=tenant_id,
        date=datetime.now(UTC).date(),
        concept=concept,
        category="cost_of_goods",
        subcategory="recipe",
        amount=total_cost,
        vat=Decimal("0"),
        total=total_cost,
        supplier_id=None,
        payment_method=payment_method,
        invoice_number=ref,
        status="paid",
        user_id=user_id,
        notes=notes,
    )
    db.add(expense)
    return expense, float(total_cost), ""


@router.post(
    "/{order_id}/checkout",
    response_model=CheckoutOrderResponse,
    status_code=201,
)
def checkout_order(
    request: Request,
    order_id: str = Path(..., pattern=_UUID_REGEX),
    payload: CheckoutOrderRequest | None = None,
    db: Session = Depends(get_db),
):
    """
    Cobra un pedido en un solo paso:

    1. Valida que el pedido exista y no esté ya cobrado/cancelado.
    2. Crea la factura automáticamente (número correlativo).
    3. Para cada producto con receta activa, calcula el costo
       (unit_cost × qty) y crea un Expense de tipo 'cost_of_goods'.
    4. Marca el pedido como 'invoiced'.

    Genérico para todos los sectores: si el producto no tiene receta
    simplemente no se genera gasto, sin errores.
    """
    from app.models.company.company_settings import CompanySettings
    from app.models.core.facturacion import Invoice
    from app.models.core.invoiceLine import LineaFactura
    from app.modules.shared.services.numbering import generar_numero_documento

    tenant_id = get_tenant_uuid(request)
    claims = getattr(request.state, "access_claims", {}) or {}
    raw_user_id = claims.get("user_id")
    try:
        user_id = UUID(str(raw_user_id)) if raw_user_id else uuid.uuid4()
    except (ValueError, AttributeError):
        user_id = uuid.uuid4()

    # --- 1. Cargar y validar pedido ---
    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID de pedido inválido")

    order: SalesOrder | None = (
        db.query(SalesOrder)
        .filter(SalesOrder.id == order_uuid, SalesOrder.tenant_id == tenant_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if order.status in _BLOCKED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"El pedido ya está en estado '{order.status}' y no puede cobrarse",
        )

    items = (
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order_uuid).all()
    )
    if not items:
        raise HTTPException(status_code=400, detail="El pedido no tiene líneas")

    # --- 2. Crear factura ---
    # Calcular totales respetando impuesto por línea
    iva_default = Decimal("0")
    settings_row = (
        db.query(CompanySettings)
        .filter(CompanySettings.tenant_id == str(tenant_id))
        .first()
    )
    settings_json = (
        settings_row.settings
        if settings_row and isinstance(settings_row.settings, dict)
        else {}
    )
    iva_default_raw = settings_json.get("iva_tasa_defecto") if isinstance(settings_json, dict) else None
    if isinstance(iva_default_raw, (int, float)):
        iva_default = Decimal(str(iva_default_raw))

    def _rate(raw: object) -> Decimal:
        r = Decimal(str(raw or 0))
        if r > 1:
            r /= Decimal("100")
        return max(r, Decimal("0"))

    subtotal = Decimal("0")
    iva_total = Decimal("0")
    for it in items:
        line_sub = Decimal(str(it.qty or 0)) * Decimal(str(it.unit_price or 0))
        r = _rate(it.tax_rate if it.tax_rate is not None else iva_default)
        subtotal += line_sub
        iva_total += line_sub * r

    total = subtotal + iva_total

    # Pre-cargar nombres de productos en un solo query
    from app.models.core.products import Product
    product_ids = [it.product_id for it in items if it.product_id]
    product_names: dict = {}
    if product_ids:
        rows = db.query(Product.id, Product.name).filter(Product.id.in_(product_ids)).all()
        product_names = {str(r.id): r.name for r in rows}

    numero = generar_numero_documento(db, tenant_id, "invoice")
    invoice = Invoice(
        number=numero,
        tenant_id=tenant_id,
        customer_id=order.customer_id,
        supplier="",
        issue_date=str(datetime.now(UTC).date()),
        amount=float(total),
        subtotal=float(subtotal),
        vat=float(iva_total),
        total=float(total),
        status="emitida",
    )
    db.add(invoice)
    db.flush()

    # Líneas de factura  ('base' es el polymorphic_identity de InvoiceLine)
    for it in items:
        line_sub = Decimal(str(it.qty or 0)) * Decimal(str(it.unit_price or 0))
        r = _rate(it.tax_rate if it.tax_rate is not None else iva_default)
        prod_name = product_names.get(str(it.product_id)) or str(it.product_id)
        db.add(
            LineaFactura(
                invoice_id=invoice.id,
                sector="base",
                description=prod_name,
                quantity=it.qty,
                unit_price=it.unit_price,
                vat=float(line_sub * r),
            )
        )

    # --- 3. Gasto de costo de receta (genérico, no falla si no hay receta) ---
    payment_method = payload.payment_method if payload else None
    import logging as _logging
    _logger = _logging.getLogger(__name__)
    expense_note: str | None = None
    try:
        _expense, expense_total, _skip_reason = _build_order_expense(
            db=db,
            order=order,
            items=items,
            tenant_id=tenant_id,
            user_id=user_id,
            invoice_number=numero,
            payment_method=payment_method,
            notes_extra=None,
        )
        expenses_created = 1 if expense_total > 0 else 0
        if not expenses_created and _skip_reason:
            expense_note = _skip_reason
    except Exception as _exp_err:
        _logger.warning("checkout_order: gasto no generado para %s: %s", order.number, _exp_err)
        expense_total = 0.0
        expenses_created = 0
        expense_note = str(_exp_err)

    # --- 4. Actualizar estado del pedido ---
    order.status = "invoiced"
    db.add(order)
    db.commit()

    return CheckoutOrderResponse(
        invoice_id=str(invoice.id),
        invoice_number=numero,
        order_id=str(order_uuid),
        expenses_created=expenses_created,
        expense_total=expense_total,
        status="ok",
        message=f"Factura {numero} generada"
        + (f" • Costo registrado: ${expense_total:.2f}" if expenses_created else ""),
        expense_note=expense_note,
    )


# Endpoint futuro para presupuestos
# @router.post("/quotes/{quote_id}/sales_order")
# def create_order_from_quote(...):
#     """Convierte presupuesto en orden de venta"""
#     pass
