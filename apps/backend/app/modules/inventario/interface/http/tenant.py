from __future__ import annotations

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.inventory.warehouse import Warehouse
from app.models.inventory.stock import StockItem, StockMove


router = APIRouter(
    prefix="/inventario",
    tags=["Inventario"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant"))],
)


def _tenant_id_str(request: Request) -> str | None:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        return str(tid) if tid is not None else None
    except Exception:
        return None


class WarehouseIn(BaseModel):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    is_active: bool = True
    metadata: Optional[dict] = None


class WarehouseOut(WarehouseIn):
    id: int

    class Config:
        from_attributes = True


@router.get("/warehouses", response_model=List[WarehouseOut])
def list_warehouses(request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    q = select(Warehouse)
    if tid is not None:
        q = q.where(Warehouse.tenant_id == tid)
    rows = db.execute(q.order_by(Warehouse.id.asc())).scalars().all()
    return rows


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseIn, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    obj = Warehouse(
        code=payload.code,
        name=payload.name,
        is_active=payload.is_active,
        extra_metadata=payload.metadata,
        tenant_id=tid,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/warehouses/{wid}", response_model=WarehouseOut)
def get_warehouse(wid: int, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    obj = db.get(Warehouse, wid)
    if not obj:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    if tid is not None and getattr(obj, "tenant_id", None) != tid:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    return obj


@router.put("/warehouses/{wid}", response_model=WarehouseOut)
def update_warehouse(wid: int, payload: WarehouseIn, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    obj = db.get(Warehouse, wid)
    if not obj:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    if tid is not None and getattr(obj, "tenant_id", None) != tid:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    obj.code = payload.code
    obj.name = payload.name
    obj.is_active = payload.is_active
    obj.extra_metadata = payload.metadata
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/warehouses/{wid}", status_code=204)
def delete_warehouse(wid: int, request: Request, db: Session = Depends(get_db)):
    tid = _tenant_id_str(request)
    obj = db.get(Warehouse, wid)
    if not obj:
        return
    if tid is not None and getattr(obj, "tenant_id", None) != tid:
        return
    db.delete(obj)
    db.commit()
    return


class StockQuery(BaseModel):
    warehouse_id: Optional[int] = None
    product_id: Optional[int] = None


class StockAdjustIn(BaseModel):
    warehouse_id: int
    product_id: int
    delta: float = Field(description="positive receipt, negative issue")
    reason: Optional[str] = None


class StockItemOut(BaseModel):
    id: int
    warehouse_id: int
    product_id: int
    qty: float

    class Config:
        from_attributes = True


@router.get("/stock", response_model=List[StockItemOut])
def get_stock(
    request: Request,
    db: Session = Depends(get_db),
    warehouse_id: Optional[int] = Query(default=None),
    product_id: Optional[int] = Query(default=None),
):
    tid = _tenant_id_str(request)
    q = select(StockItem)
    if tid is not None:
        q = q.where(StockItem.tenant_id == tid)
    if warehouse_id is not None:
        q = q.where(StockItem.warehouse_id == warehouse_id)
    if product_id is not None:
        q = q.where(StockItem.product_id == product_id)
    rows = db.execute(q.order_by(StockItem.id.asc())).scalars().all()
    return rows


@router.post("/stock/adjust", response_model=StockItemOut)
def adjust_stock(payload: StockAdjustIn, request: Request, db: Session = Depends(get_db)):
    # Find or create stock item
    tid = _tenant_id_str(request)
    row = (
        db.query(StockItem)
        .filter(
            StockItem.warehouse_id == payload.warehouse_id,
            StockItem.product_id == payload.product_id,
        )
        .first()
    )
    if not row:
        row = StockItem(warehouse_id=payload.warehouse_id, product_id=payload.product_id, qty=0, tenant_id=tid)
        db.add(row)
        db.flush()

    # Create move
    kind = "receipt" if payload.delta >= 0 else "issue"
    move = StockMove(
        tenant_id=tid,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        qty=abs(payload.delta),
        kind=kind,
        tentative=False,
        ref_type="adjust",
        ref_id=payload.reason or None,
    )
    db.add(move)

    # Update stock qty
    row.qty = (row.qty or 0) + payload.delta
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
