from __future__ import annotations

from typing import List, Optional
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.sales.order import SalesOrder, SalesOrderItem
from app.models.sales.delivery import Delivery
from app.models.inventory.stock import StockMove, StockItem


router = APIRouter(
    prefix="/ventas",
    tags=["Sales"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
)


def _tenant_id_str(request: Request) -> str | None:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        return str(tid) if tid is not None else None
    except Exception:
        return None


class OrderItemIn(BaseModel):
    product_id: int
    qty: float = Field(gt=0)
    unit_price: float = 0


class OrderCreateIn(BaseModel):
    customer_id: Optional[int] = None
    currency: Optional[str] = None
    items: List[OrderItemIn]


class OrderOut(BaseModel):
    id: int
    status: str
    customer_id: Optional[int]
    currency: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[OrderOut])
def list_orders(
    request: Request,
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
):
    """Listar órdenes de venta"""
    tid = _tenant_id_str(request)
    
    query = db.query(SalesOrder).filter(SalesOrder.tenant_id == tid)
    
    if status:
        query = query.filter(SalesOrder.status == status)
    
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    
    orders = query.order_by(SalesOrder.created_at.desc()).offset(offset).limit(limit).all()
    
    return orders


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    """Obtener orden de venta por ID"""
    tid = _tenant_id_str(request)
    
    order = db.query(SalesOrder).filter(
        SalesOrder.id == order_id,
        SalesOrder.tenant_id == tid
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    return order


@router.post("/", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreateIn, request: Request, db: Session = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items_required")
    tid = _tenant_id_str(request)
    so = SalesOrder(customer_id=payload.customer_id, currency=payload.currency, status="draft", tenant_id=tid)
    db.add(so)
    db.flush()
    for it in payload.items:
        db.add(SalesOrderItem(order_id=so.id, product_id=it.product_id, qty=it.qty, unit_price=it.unit_price, tenant_id=tid))
    db.commit()
    db.refresh(so)
    return so


class ConfirmIn(BaseModel):
    warehouse_id: int


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, payload: ConfirmIn, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    so = db.get(SalesOrder, order_id)
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
    return so


deliveries_router = APIRouter(
    prefix="/deliveries",
    tags=["Deliveries"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant")), Depends(ensure_rls)],
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
def do_delivery(delivery_id: int, payload: DeliverIn, request: Request, db: Session = Depends(get_db)):
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
    for it in items:
        mv = StockMove(
            tenant_id=tid,
            product_id=it.product_id,
            warehouse_id=payload.warehouse_id,
            qty=it.qty,
            kind="issue",
            tentative=False,
            ref_type="delivery",
            ref_id=str(delivery_id),
        )
        db.add(mv)
        # update stock item
        row = (
            db.query(StockItem)
            .filter(StockItem.warehouse_id == payload.warehouse_id, StockItem.product_id == it.product_id)
            .first()
        )
        if not row:
            row = StockItem(warehouse_id=payload.warehouse_id, product_id=it.product_id, qty=0)
            db.add(row)
            db.flush()
        row.qty = (row.qty or 0) - it.qty
        db.add(row)

    d.status = "done"
    so.status = "delivered"
    db.add(d)
    db.add(so)
    db.commit()
    return {"delivery_id": delivery_id, "status": d.status}
