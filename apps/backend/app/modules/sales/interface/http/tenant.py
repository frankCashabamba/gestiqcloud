from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.clients import Client
from app.models.inventory.stock import StockItem, StockMove
from app.models.sales.delivery import Delivery
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.services.inventory_costing import InventoryCostingService

router = APIRouter(
    prefix="/sales_orders",
    tags=["Sales"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _tenant_id_str(request: Request) -> str | None:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        return str(tid) if tid is not None else None
    except Exception:
        return None


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _dec(value: float | Decimal | None, q: str = "0.000001") -> Decimal:
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


class OrderItemIn(BaseModel):
    product_id: str
    qty: float = Field(gt=0)
    unit_price: float = 0


class OrderCreateIn(BaseModel):
    customer_id: str | None = None
    currency: str | None = None
    items: list[OrderItemIn]


class OrderOut(BaseModel):
    id: str
    number: str | None = None
    order_date: date | None = None
    created_at: str | None = None
    status: str
    customer_id: str | None
    customer_name: str | None = None
    pos_receipt_id: str | None = None
    currency: str | None
    subtotal: float | None = None
    tax: float | None = None
    total: float | None = None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[OrderOut])
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    status: str | None = None,
    customer_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Listar órdenes de venta"""
    tid = _tenant_id_str(request)

    tenant_uuid = UUID(str(tid)) if tid else None
    if not tenant_uuid:
        raise HTTPException(status_code=401, detail="tenant_id invalido")
    query = (
        db.query(SalesOrder, Client.name)
        .outerjoin(Client, Client.id == SalesOrder.customer_id)
        .filter(SalesOrder.tenant_id == tenant_uuid)
    )

    if status:
        query = query.filter(SalesOrder.status == status)

    if customer_id:
        query = query.filter(SalesOrder.customer_id == _uuid_or_none(customer_id))

    rows = query.order_by(SalesOrder.created_at.desc()).offset(offset).limit(limit).all()

    return [
        OrderOut(
            id=str(o.id),
            number=getattr(o, "number", None),
            order_date=getattr(o, "order_date", None),
            created_at=o.created_at.isoformat() if getattr(o, "created_at", None) else None,
            status=o.status,
            customer_id=str(o.customer_id) if o.customer_id else None,
            customer_name=customer_name,
            pos_receipt_id=str(o.pos_receipt_id) if getattr(o, "pos_receipt_id", None) else None,
            currency=o.currency,
            subtotal=float(o.subtotal or 0),
            tax=float(o.tax or 0),
            total=float(o.total or 0),
        )
        for (o, customer_name) in rows
    ]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    request: Request,
    order_id: str = Path(
        ..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    db: Session = Depends(get_db),
):
    """Obtener orden de venta por ID"""
    tid = _tenant_id_str(request)
    tenant_uuid = UUID(str(tid)) if tid else None
    if not tenant_uuid:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

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
    return OrderOut(
        id=str(order.id),
        number=getattr(order, "number", None),
        order_date=getattr(order, "order_date", None),
        created_at=order.created_at.isoformat() if getattr(order, "created_at", None) else None,
        status=order.status,
        customer_id=str(order.customer_id) if order.customer_id else None,
        customer_name=customer_name,
        pos_receipt_id=str(order.pos_receipt_id)
        if getattr(order, "pos_receipt_id", None)
        else None,
        currency=order.currency,
        subtotal=float(order.subtotal or 0),
        tax=float(order.tax or 0),
        total=float(order.total or 0),
    )


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreateIn, request: Request, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items_required")
    tid = _tenant_id_str(request)
    tenant_uuid = UUID(str(tid)) if tid else None
    if not tenant_uuid:
        raise HTTPException(status_code=401, detail="tenant_id invalido")
    so = SalesOrder(
        customer_id=_uuid_or_none(payload.customer_id),
        currency=payload.currency,
        status="draft",
        tenant_id=tenant_uuid,
        number=f"SO-{str(tenant_uuid)[:8]}-{uuid4().hex[:6]}",
        order_date=date.today(),
    )
    db.add(so)
    db.flush()
    for it in payload.items:
        db.add(
            SalesOrderItem(
                order_id=so.id,
                product_id=_uuid_or_none(it.product_id),
                qty=it.qty,
                unit_price=it.unit_price,
            )
        )
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

    return OrderOut(
        id=str(so.id),
        number=so.number,
        order_date=so.order_date,
        created_at=so.created_at.isoformat() if getattr(so, "created_at", None) else None,
        status=so.status,
        customer_id=str(so.customer_id) if so.customer_id else None,
        customer_name=(
            db.query(Client.name).filter(Client.id == so.customer_id).scalar()
            if so.customer_id
            else None
        ),
        pos_receipt_id=str(so.pos_receipt_id) if getattr(so, "pos_receipt_id", None) else None,
        currency=so.currency,
        subtotal=float(so.subtotal or 0),
        tax=float(so.tax or 0),
        total=float(so.total or 0),
    )


class ConfirmIn(BaseModel):
    warehouse_id: str


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(
    order_id: str = Path(
        ..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    payload: ConfirmIn | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    if request is None:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

    tid = _tenant_id_str(request)
    tenant_uuid = UUID(str(tid)) if tid else None
    if not tenant_uuid:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

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
    if tid and str(getattr(so, "tenant_id", None)) != tid:
        raise HTTPException(status_code=404, detail="order_not_found")
    if so.status != "draft":
        raise HTTPException(status_code=400, detail="invalid_status")
    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == order_id).all()
    if not items:
        raise HTTPException(status_code=400, detail="no_items")
    for it in items:
        mv = StockMove(
            tenant_id=tid,
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
    order_id: int


@deliveries_router.post("/", response_model=dict, status_code=201)
def create_delivery(payload: DeliveryCreateIn, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    so = db.get(SalesOrder, payload.order_id)
    if not so or so.status != "confirmed":
        raise HTTPException(status_code=400, detail="order_not_confirmed")
    if tid and str(getattr(so, "tenant_id", None)) != tid:
        raise HTTPException(status_code=404, detail="order_not_found")
    d = Delivery(order_id=payload.order_id, status="pending", tenant_id=tid)
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
    tid = _tenant_id_str(request)
    d = db.get(Delivery, delivery_id)
    if not d or d.status != "pending":
        raise HTTPException(status_code=404, detail="delivery_not_pending")
    if tid and str(getattr(d, "tenant_id", None)) != tid:
        raise HTTPException(status_code=404, detail="delivery_not_pending")
    so = db.get(SalesOrder, d.order_id)
    if not so or so.status != "confirmed":
        raise HTTPException(status_code=400, detail="order_not_confirmed")
    if tid and str(getattr(so, "tenant_id", None)) != tid:
        raise HTTPException(status_code=404, detail="order_not_found")

    items = db.query(SalesOrderItem).filter(SalesOrderItem.order_id == so.id).all()
    # Consume stock: for each item, create issue move and update stock_items
    costing = InventoryCostingService(db)
    for it in items:
        qty_dec = _dec(it.qty)
        row = (
            db.query(StockItem)
            .filter(
                StockItem.warehouse_id == payload.warehouse_id,
                StockItem.product_id == it.product_id,
            )
            .with_for_update()
            .first()
        )
        if not row:
            row = StockItem(warehouse_id=payload.warehouse_id, product_id=it.product_id, qty=0)
            db.add(row)
            db.flush()

        state = costing.apply_outbound(
            tid or "",
            str(payload.warehouse_id),
            str(it.product_id),
            qty=qty_dec,
            allow_negative=False,
            initial_qty=_dec(row.qty),
            initial_avg_cost=_dec(0),
        )

        mv = StockMove(
            tenant_id=tid,
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

    d.status = "done"
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
        ..., regex="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    ),
    payload: CancelIn | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Cancel a sales order"""
    if request is None:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

    tid = _tenant_id_str(request)
    tenant_uuid = UUID(str(tid)) if tid else None
    if not tenant_uuid:
        raise HTTPException(status_code=401, detail="tenant_id invalido")

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

    return OrderOut(
        id=str(so.id),
        number=so.number,
        order_date=so.order_date,
        created_at=so.created_at.isoformat() if getattr(so, "created_at", None) else None,
        status=so.status,
        customer_id=str(so.customer_id) if so.customer_id else None,
        customer_name=(
            db.query(Client.name).filter(Client.id == so.customer_id).scalar()
            if so.customer_id
            else None
        ),
        pos_receipt_id=str(so.pos_receipt_id) if getattr(so, "pos_receipt_id", None) else None,
        currency=so.currency,
        subtotal=float(so.subtotal or 0),
        tax=float(so.tax or 0),
        total=float(so.total or 0),
    )
