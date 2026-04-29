from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.dependencies import get_tenant_uuid
from app.db.rls import ensure_rls
from app.models.core.clients import Client
from app.models.core.products import Product
from app.models.inventory.stock import StockItem, StockMove
from app.models.sales.delivery import Delivery
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.modules.shared.services.statuses import DeliveryStatus
from app.modules.shared.services.tax import normalize_tax_rate, resolve_tenant_default_tax_rate
from app.services.inventory_costing import InventoryCostingService
from app.shared.utils import to_decimal as _dec

router = APIRouter(
    prefix="/sales_orders",
    tags=["Sales"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _resolve_delivery_stock_item(
    db: Session,
    *,
    tenant_id: UUID,
    warehouse_id: int,
    product_id: str,
) -> tuple[StockItem | None, Decimal]:
    rows = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tenant_id,
            StockItem.warehouse_id == warehouse_id,
            StockItem.product_id == product_id,
        )
        .with_for_update()
        .all()
    )
    total_qty = _dec(sum(float(row.qty or 0) for row in rows))
    positive_rows = [row for row in rows if float(row.qty or 0) > 0]
    if len(positive_rows) > 1:
        raise HTTPException(status_code=409, detail="lot_selection_required")
    if positive_rows:
        return positive_rows[0], total_qty
    return (rows[0] if rows else None), total_qty


class OrderItemOut(BaseModel):
    product_id: str
    product_name: str | None = None
    qty: float
    unit_price: float
    discount_pct: float = 0
    tax_rate: float = 0
    line_total: float = 0


class OrderItemIn(BaseModel):
    product_id: str
    qty: float = Field(gt=0)
    unit_price: float = 0
    discount_pct: float = Field(default=0, ge=0, le=100)
    tax_rate: float | None = Field(default=None, ge=0)


class OrderCreateIn(BaseModel):
    customer_id: str | None = None
    currency: str | None = None
    notes: str | None = None
    required_date: date | None = None
    deposit_amount: float = 0
    deposit_paid: bool = False
    payment_method: str | None = None
    items: list[OrderItemIn] = []


class OrderOut(BaseModel):
    id: str
    number: str | None = None
    order_date: date | None = None
    required_date: date | None = None
    created_at: str | None = None
    updated_at: str | None = None
    status: str
    customer_id: str | None
    customer_name: str | None = None
    pos_receipt_id: str | None = None
    currency: str | None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None
    notes: str | None = None
    deposit_amount: float = 0
    deposit_paid: bool = False
    payment_method: str | None = None
    items: list[OrderItemOut] = []

    model_config = {"from_attributes": True}


class OrderUpdateIn(BaseModel):
    customer_id: str | None = None
    currency: str | None = None
    notes: str | None = None
    required_date: date | None = None
    deposit_amount: float | None = None
    deposit_paid: bool | None = None
    payment_method: str | None = None
    status: str | None = None
    items: list[OrderItemIn] | None = None


def _order_out(
    o: SalesOrder, customer_name: str | None = None, db: Session | None = None
) -> OrderOut:
    items: list[OrderItemOut] = []
    if db is not None:
        # Batch-load items + product names in 2 queries (avoid N+1 per product)
        rows = (
            db.query(SalesOrderItem, Product.name)
            .outerjoin(Product, Product.id == SalesOrderItem.product_id)
            .filter(SalesOrderItem.order_id == o.id)
            .all()
        )
        for it, prod_name in rows:
            items.append(
                OrderItemOut(
                    product_id=str(it.product_id),
                    product_name=prod_name,
                    qty=float(it.qty or 0),
                    unit_price=float(it.unit_price or 0),
                    discount_pct=float(it.discount_percent or 0),
                    tax_rate=float(it.tax_rate or 0),
                    line_total=float(it.line_total or 0),
                )
            )
    return OrderOut(
        id=str(o.id),
        number=getattr(o, "number", None),
        order_date=getattr(o, "order_date", None),
        required_date=getattr(o, "required_date", None),
        created_at=o.created_at.isoformat() if getattr(o, "created_at", None) else None,
        updated_at=o.updated_at.isoformat() if getattr(o, "updated_at", None) else None,
        status=o.status,
        customer_id=str(o.customer_id) if o.customer_id else None,
        customer_name=customer_name,
        pos_receipt_id=str(o.pos_receipt_id) if getattr(o, "pos_receipt_id", None) else None,
        currency=o.currency,
        subtotal=float(o.subtotal or 0),
        tax=float(o.tax or 0),
        total=float(o.total or 0),
        notes=getattr(o, "notes", None),
        deposit_amount=float(getattr(o, "deposit_amount", 0) or 0),
        deposit_paid=bool(getattr(o, "deposit_paid", False)),
        payment_method=getattr(o, "payment_method", None),
        items=items,
    )


@router.get("", response_model=list[OrderOut])
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = None,
    customer_id: str | None = None,
    limit: int = 50,
    skip: int = 0,
    offset: int = 0,
):
    """Listar Ã³rdenes de venta"""
    tenant_uuid = get_tenant_uuid(request)
    query = (
        db.query(SalesOrder, Client.name)
        .outerjoin(Client, Client.id == SalesOrder.customer_id)
        .filter(SalesOrder.tenant_id == tenant_uuid)
    )

    if status:
        query = query.filter(SalesOrder.status == status)

    if customer_id:
        query = query.filter(SalesOrder.customer_id == _uuid_or_none(customer_id))

    effective_offset = skip or offset
    rows = query.order_by(SalesOrder.created_at.desc()).offset(effective_offset).limit(min(limit, 200)).all()

    if not rows:
        return []

    # Cargar items en batch (evita N+1)
    order_ids = [o.id for (o, _) in rows]
    all_items = (
        db.query(SalesOrderItem, Product.name)
        .outerjoin(Product, Product.id == SalesOrderItem.product_id)
        .filter(SalesOrderItem.order_id.in_(order_ids))
        .all()
    )
    items_by_order: dict = {}
    for it, prod_name in all_items:
        oid = str(it.order_id)
        items_by_order.setdefault(oid, []).append(
            OrderItemOut(
                product_id=str(it.product_id),
                product_name=prod_name,
                qty=float(it.qty or 0),
                unit_price=float(it.unit_price or 0),
                discount_pct=float(it.discount_percent or 0),
                tax_rate=float(it.tax_rate or 0),
                line_total=float(it.line_total or 0),
            )
        )

    result = []
    for o, customer_name in rows:
        out = _order_out(o, customer_name)
        out.items = items_by_order.get(str(o.id), [])
        result.append(out)
    return result


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    request: Request,
    order_id: str = Path(
        ..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    db: Session = Depends(get_db),
):
    """Obtener orden de venta por ID"""
    tenant_uuid = get_tenant_uuid(request)

    try:
        order_uuid = UUID(str(order_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    row = (
        db.query(SalesOrder, Client.name)
        .outerjoin(Client, Client.id == SalesOrder.customer_id)
        .filter(SalesOrder.id == order_uuid, SalesOrder.tenant_id == tenant_uuid)
        .first()
    )

    if not row:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    order, customer_name = row
    return _order_out(order, customer_name, db=db)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreateIn, request: Request, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items_required")
    tenant_uuid = get_tenant_uuid(request)
    default_tax_rate = resolve_tenant_default_tax_rate(db, tenant_uuid)
    so = SalesOrder(
        customer_id=_uuid_or_none(payload.customer_id),
        currency=payload.currency,
        status="draft",
        tenant_id=tenant_uuid,
        number=f"SO-{str(tenant_uuid)[:8]}-{uuid4().hex[:6]}",
        order_date=date.today(),
        notes=payload.notes,
        required_date=payload.required_date,
        deposit_amount=payload.deposit_amount,
        deposit_paid=payload.deposit_paid,
        payment_method=payload.payment_method,
    )
    db.add(so)
    db.flush()
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for it in payload.items:
        line_sub = _dec(it.qty, "0.01") * _dec(it.unit_price, "0.01")
        discount_amount = line_sub * _dec(it.discount_pct, "0.01") / Decimal("100")
        line_total = line_sub - discount_amount
        line_tax_rate = normalize_tax_rate(it.tax_rate)
        effective_tax_rate = line_tax_rate if line_tax_rate is not None else default_tax_rate
        line_tax = line_total * effective_tax_rate
        subtotal += line_total
        tax_total += line_tax
        db.add(
            SalesOrderItem(
                order_id=so.id,
                product_id=_uuid_or_none(it.product_id),
                qty=it.qty,
                unit_price=it.unit_price,
                tax_rate=float(effective_tax_rate),
                discount_percent=it.discount_pct,
                line_total=float(line_total),
            )
        )
    so.subtotal = float(subtotal)
    so.tax = float(tax_total)
    so.total = float(subtotal + tax_total)
    db.commit()
    db.refresh(so)

    # Trigger sales_order.created webhook
    try:
        from app.modules.sales.webhooks import SalesOrderWebhookService

        customer_name = (
            db.query(Client.name).filter(Client.id == so.customer_id).scalar()
            if so.customer_id
            else None
        )
        webhook_service = SalesOrderWebhookService(db)
        webhook_service.trigger_sales_order_created(
            tenant_id=tenant_uuid,
            order_id=str(so.id),
            order_number=so.number or str(so.id),
            customer_id=str(so.customer_id) if so.customer_id else None,
            customer_name=customer_name,
            amount=float(so.total or 0),
            currency=so.currency or "USD",
            items_count=len(payload.items),
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error triggering sales_order.created webhook: {e}")

    customer_name = (
        db.query(Client.name).filter(Client.id == so.customer_id).scalar()
        if so.customer_id
        else None
    )

    # NotificaciÃ³n Telegram nuevo pedido (best-effort, non-blocking)
    try:
        product_ids = [_uuid_or_none(it.product_id) for it in payload.items if it.product_id]
        product_names: dict = {}
        if product_ids:
            rows = db.query(Product.id, Product.name).filter(Product.id.in_(product_ids)).all()
            product_names = {str(r.id): r.name for r in rows}
        tg_items = [
            {
                "name": product_names.get(str(_uuid_or_none(it.product_id)), "Producto"),
                "qty": it.qty,
            }
            for it in payload.items
        ]
        _notify_new_order_telegram(
            db=db,
            tenant_id=tenant_uuid,
            order_number=so.number or str(so.id),
            customer_name=customer_name,
            total=float(so.total or 0),
            currency=so.currency or "USD",
            items=tg_items,
            payment_method=so.payment_method,
            notes=so.notes,
        )
    except Exception as _tg_err:
        import logging

        logging.getLogger(__name__).warning(
            "Telegram new-order notification failed (non-fatal): %s", _tg_err
        )

    return _order_out(so, customer_name)


@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    payload: OrderUpdateIn,
    order_id: str = Path(
        ..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Actualizar campos de una orden (notas, fecha entrega, anticipo, estado)"""
    if request is None:
        raise HTTPException(status_code=401, detail="tenant_id invalido")
    tenant_uuid = get_tenant_uuid(request)
    try:
        so_id = UUID(str(order_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    so = (
        db.query(SalesOrder)
        .filter(SalesOrder.id == so_id, SalesOrder.tenant_id == tenant_uuid)
        .first()
    )
    if not so:
        raise HTTPException(status_code=404, detail="order_not_found")
    # Ventas del POS bloqueadas excepto si son borrador (pendiente de cobro mayorista)
    if getattr(so, "pos_receipt_id", None) is not None and so.status != "draft":
        raise HTTPException(status_code=403, detail="pos_sale_readonly")
    if payload.customer_id is not None:
        so.customer_id = _uuid_or_none(payload.customer_id)
    if payload.currency is not None:
        so.currency = payload.currency
    if payload.notes is not None:
        so.notes = payload.notes
    if payload.required_date is not None:
        so.required_date = payload.required_date
    if payload.deposit_amount is not None:
        so.deposit_amount = payload.deposit_amount
    if payload.deposit_paid is not None:
        so.deposit_paid = payload.deposit_paid
    if payload.payment_method is not None:
        so.payment_method = payload.payment_method
    if payload.status is not None:
        allowed = {"draft", "confirmed", "cancelled"}
        if payload.status not in allowed:
            raise HTTPException(status_code=400, detail="invalid_status")
        so.status = payload.status

    # Actualizar lÃ­neas si se envÃ­an
    if payload.items is not None:
        db.query(SalesOrderItem).filter(SalesOrderItem.order_id == so_id).delete()
        default_tax_rate = resolve_tenant_default_tax_rate(db, tenant_uuid)
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        for it in payload.items:
            line_sub = _dec(it.qty, "0.01") * _dec(it.unit_price, "0.01")
            discount_amount = line_sub * _dec(it.discount_pct, "0.01") / Decimal("100")
            line_total = line_sub - discount_amount
            line_tax_rate = normalize_tax_rate(it.tax_rate)
            effective_tax_rate = line_tax_rate if line_tax_rate is not None else default_tax_rate
            line_tax = line_total * effective_tax_rate
            subtotal += line_total
            tax_total += line_tax
            db.add(
                SalesOrderItem(
                    order_id=so.id,
                    product_id=_uuid_or_none(it.product_id),
                    qty=it.qty,
                    unit_price=it.unit_price,
                    tax_rate=float(effective_tax_rate),
                    discount_percent=it.discount_pct,
                    line_total=float(line_total),
                )
            )
        so.subtotal = float(subtotal)
        so.tax = float(tax_total)
        so.total = float(subtotal + tax_total)

    db.add(so)
    db.commit()
    db.refresh(so)
    customer_name = (
        db.query(Client.name).filter(Client.id == so.customer_id).scalar()
        if so.customer_id
        else None
    )
    return _order_out(so, customer_name, db=db)


class ConfirmIn(BaseModel):
    warehouse_id: str


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(
    order_id: str = Path(
        ..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    payload: ConfirmIn | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    if request is None:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

    tenant_uuid = get_tenant_uuid(request)

    try:
        so_id = UUID(str(order_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    so = (
        db.query(SalesOrder)
        .filter(SalesOrder.id == so_id, SalesOrder.tenant_id == tenant_uuid)
        .first()
    )
    if not so:
        raise HTTPException(status_code=404, detail="order_not_found")
    if so.status != "draft":
        raise HTTPException(status_code=400, detail="invalid_status")
    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == so_id).all()
    if not items:
        raise HTTPException(status_code=400, detail="no_items")
    for it in items:
        mv = StockMove(
            tenant_id=str(tenant_uuid),
            product_id=it.product_id,
            warehouse_id=payload.warehouse_id,
            qty=it.qty,
            kind="reserve",
            tentative=True,
            ref_type="sales_order",
            ref_id=str(order_id),
        )
        db.add(mv)
    so.status = "confirmed"
    db.add(so)
    db.commit()
    db.refresh(so)

    # Trigger sales_order.confirmed webhook
    try:
        from app.modules.sales.webhooks import SalesOrderWebhookService

        customer_name = (
            db.query(Client.name).filter(Client.id == so.customer_id).scalar()
            if so.customer_id
            else None
        )
        webhook_service = SalesOrderWebhookService(db)
        webhook_service.trigger_sales_order_confirmed(
            tenant_id=tenant_uuid,
            order_id=str(so.id),
            order_number=so.number or str(so.id),
            customer_id=str(so.customer_id) if so.customer_id else None,
            customer_name=customer_name,
            amount=float(so.total or 0),
            currency=so.currency or "USD",
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error triggering sales_order.confirmed webhook: {e}")

    return so


deliveries_router = APIRouter(
    prefix="/deliveries",
    tags=["Deliveries"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


class DeliveryCreateIn(BaseModel):
    order_id: UUID


@deliveries_router.post("/", response_model=dict, status_code=201)
def create_delivery(payload: DeliveryCreateIn, request: Request, db: Session = Depends(get_db)):
    tenant_uuid = get_tenant_uuid(request)
    so = db.get(SalesOrder, payload.order_id)
    if not so or so.status != "confirmed":
        raise HTTPException(status_code=400, detail="order_not_confirmed")
    if str(getattr(so, "tenant_id", None)) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="order_not_found")
    d = Delivery(
        order_id=payload.order_id,
        status=DeliveryStatus.PENDING.value,
        tenant_id=str(tenant_uuid),
    )
    db.add(d)
    db.commit()
    return {"id": d.id, "status": d.status}


class DeliverIn(BaseModel):
    warehouse_id: int


@deliveries_router.post("/{delivery_id}/deliver", response_model=dict)
def do_delivery(
    delivery_id: int,
    payload: DeliverIn,
    request: Request,
    db: Session = Depends(get_db),
):
    tenant_uuid = get_tenant_uuid(request)
    d = db.get(Delivery, delivery_id)
    if not d or d.status != DeliveryStatus.PENDING.value:
        raise HTTPException(status_code=404, detail="delivery_not_pending")
    if str(getattr(d, "tenant_id", None)) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="delivery_not_pending")
    so = db.get(SalesOrder, d.order_id)
    if not so or so.status != "confirmed":
        raise HTTPException(status_code=400, detail="order_not_confirmed")
    if str(getattr(so, "tenant_id", None)) != str(tenant_uuid):
        raise HTTPException(status_code=404, detail="order_not_found")

    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == so.id).all()
    # Consume stock: for each item, create issue move and update stock_items
    costing = InventoryCostingService(db)
    for it in items:
        qty_dec = _dec(it.qty)
        row, total_qty = _resolve_delivery_stock_item(
            db,
            tenant_id=tenant_uuid,
            warehouse_id=payload.warehouse_id,
            product_id=it.product_id,
        )
        if not row:
            row = StockItem(
                tenant_id=tenant_uuid,
                warehouse_id=payload.warehouse_id,
                product_id=it.product_id,
                qty=0,
            )
            db.add(row)
            db.flush()

        state = costing.apply_outbound(
            str(tenant_uuid),
            str(payload.warehouse_id),
            str(it.product_id),
            qty=qty_dec,
            allow_negative=False,
            initial_qty=total_qty,
            initial_avg_cost=_dec(0),
        )

        mv = StockMove(
            tenant_id=str(tenant_uuid),
            product_id=it.product_id,
            warehouse_id=payload.warehouse_id,
            qty=it.qty,
            kind="issue",
            tentative=False,
            ref_type="delivery",
            ref_id=str(delivery_id),
            unit_cost=float(state.avg_cost),
            total_cost=float(state.avg_cost * qty_dec),
        )
        db.add(mv)

        row.qty = (row.qty or 0) - it.qty
        db.add(row)

    d.status = DeliveryStatus.DONE.value
    so.status = "delivered"
    db.add(d)
    db.add(so)
    db.commit()
    return {"delivery_id": delivery_id, "status": d.status}


class CancelIn(BaseModel):
    reason: str | None = None


@router.put("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: str = Path(
        ..., pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    payload: CancelIn | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Cancel a sales order"""
    if request is None:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

    tenant_uuid = get_tenant_uuid(request)

    try:
        so_id = UUID(str(order_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    so = (
        db.query(SalesOrder)
        .filter(SalesOrder.id == so_id, SalesOrder.tenant_id == tenant_uuid)
        .first()
    )
    if not so:
        raise HTTPException(status_code=404, detail="order_not_found")

    if so.status == "delivered":
        raise HTTPException(status_code=400, detail="Cannot cancel delivered order")

    so.status = "cancelled"
    db.add(so)
    db.commit()
    db.refresh(so)

    # Trigger sales_order.cancelled webhook
    try:
        from app.modules.sales.webhooks import SalesOrderWebhookService

        webhook_service = SalesOrderWebhookService(db)
        webhook_service.trigger_sales_order_cancelled(
            tenant_id=tenant_uuid,
            order_id=str(so.id),
            order_number=so.number or str(so.id),
            reason=payload.reason if payload else None,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error triggering sales_order.cancelled webhook: {e}")

    customer_name_c = (
        db.query(Client.name).filter(Client.id == so.customer_id).scalar()
        if so.customer_id
        else None
    )
    return _order_out(so, customer_name_c)


def _notify_new_order_telegram(
    *,
    db: Session,
    tenant_id,
    order_number: str,
    customer_name: str | None,
    total: float,
    currency: str,
    items: list[dict],
    payment_method: str | None,
    notes: str | None,
) -> None:
    """Envia notificacion Telegram cuando se crea un nuevo pedido."""
    from app.models.ai.incident import NotificationChannel
    from app.modules.notifications.infrastructure._transport import send_telegram

    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.tenant_id == tenant_id,
            NotificationChannel.channel_type == "telegram",
            NotificationChannel.is_active.is_(True),
        )
        .first()
    )
    if not channel:
        return

    config = channel.config or {}
    chat_id = config.get("default_recipient")
    if not chat_id:
        return

    safe_customer = escape(str(customer_name)) if customer_name else ""
    safe_payment = escape(str(payment_method)) if payment_method else ""
    safe_notes = escape(str(notes)) if notes else ""
    safe_order_number = escape(str(order_number))
    safe_currency = escape(str(currency))
    items_lines = "".join(
        f"  - {escape(str(it.get('name', '')))} x{float(it.get('qty') or 0):g}\n"
        for it in items
    )

    cliente_line = f"Cliente: <b>{safe_customer}</b>\n" if safe_customer else ""
    metodo_line = f"Pago: {safe_payment}\n" if safe_payment else ""
    notas_line = f"Notas: {safe_notes}\n" if safe_notes else ""

    message = (
        "<b>Nuevo Pedido</b>\n"
        f"Numero: <b>{safe_order_number}</b>\n"
        f"{cliente_line}"
        f"Productos:\n{items_lines}"
        f"Total: <b>{safe_currency} {total:,.2f}</b>\n"
        f"{metodo_line}"
        f"{notas_line}"
    )

    send_telegram(config, chat_id, message.strip())
