from __future__ import annotations

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.core.products import Product
from app.models.inventory.stock import StockItem, StockMove
from app.models.inventory.warehouse import Warehouse
from app.services.inventory_costing import InventoryCostingService

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("tenant"))],
)


def _tenant_id_str(request: Request) -> str | None:
    try:
        claims = getattr(request.state, "access_claims", None) or {}
        tid = claims.get("tenant_id") if isinstance(claims, dict) else None
        return str(tid) if tid is not None else None
    except Exception:
        return None


def _require_tenant_id(request: Request) -> str:
    tid = _tenant_id_str(request)
    if tid is None:
        raise HTTPException(status_code=403, detail="missing_tenant")
    return tid


def _dec(value: float | Decimal | None, q: str = "0.000001") -> Decimal:
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


class WarehouseIn(BaseModel):
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    is_active: bool = True
    metadata: dict | None = None


class WarehouseOut(WarehouseIn):
    # Accept UUID from ORM and serialize as string
    id: UUID
    # Map SQLAlchemy attribute 'extra_metadata' to API field 'metadata'
    metadata: dict | None = Field(default=None, validation_alias="extra_metadata")

    model_config = {"from_attributes": True}


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    q = select(Warehouse)
    if tid is not None:
        q = q.where(Warehouse.tenant_id == tid)
    rows = db.execute(q.order_by(Warehouse.id.asc())).scalars().all()
    return rows


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseIn, request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    obj = Warehouse(
        code=payload.code,
        name=payload.name,
        is_active=payload.is_active,
        extra_metadata=payload.metadata,
        tenant_id=tid,
    )
    # Ensure primary key is present even if DB/defaults are misconfigured
    if not getattr(obj, "id", None):
        try:
            obj.id = uuid4()
        except Exception:
            pass
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/warehouses/{wid}", response_model=WarehouseOut)
def get_warehouse(wid: UUID, request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    obj = db.get(Warehouse, wid)
    if not obj:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    if tid is not None and getattr(obj, "tenant_id", None) != tid:
        raise HTTPException(status_code=404, detail="warehouse_not_found")
    return obj


@router.put("/warehouses/{wid}", response_model=WarehouseOut)
def update_warehouse(
    wid: UUID, payload: WarehouseIn, request: Request, db: Session = Depends(get_db)
):
    tid = _require_tenant_id(request)
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
def delete_warehouse(wid: UUID, request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    obj = db.get(Warehouse, wid)
    if not obj:
        return
    if tid is not None and getattr(obj, "tenant_id", None) != tid:
        return
    db.delete(obj)
    db.commit()
    return


class StockQuery(BaseModel):
    warehouse_id: str | None = None
    product_id: str | None = None


class StockAdjustIn(BaseModel):
    warehouse_id: str
    product_id: str
    delta: float = Field(description="positive receipt, negative issue")
    unit_cost: float | None = Field(default=None, description="optional unit cost for receipts")
    reason: str | None = None


class StockItemOut(BaseModel):
    id: str
    warehouse_id: str
    product_id: str
    qty: float
    ubicacion: str | None = None
    lote: str | None = None
    expires_at: str | None = None
    product: dict | None = None
    warehouse: dict | None = None


@router.get("/stock", response_model=list[StockItemOut])
def get_stock(
    request: Request,
    db: Session = Depends(get_db),
    warehouse_id: str | None = Query(default=None),
    product_id: str | None = Query(default=None),
):
    tid = _require_tenant_id(request)
    # Join to enrich with product and warehouse info
    q = (
        select(
            StockItem.id,
            StockItem.product_id,
            StockItem.warehouse_id,
            StockItem.qty,
            Product.sku.label("p_sku"),
            Product.name.label("p_name"),
            Product.price.label("p_price"),
            Product.product_metadata.label("p_meta"),
            Warehouse.code.label("w_code"),
            Warehouse.name.label("w_name"),
        )
        .join(Product, Product.id == StockItem.product_id)
        .join(Warehouse, Warehouse.id == StockItem.warehouse_id)
    )
    if tid is not None:
        q = q.where(StockItem.tenant_id == tid)
    if warehouse_id is not None:
        q = q.where(StockItem.warehouse_id == warehouse_id)
    if product_id is not None:
        q = q.where(StockItem.product_id == product_id)
    q = q.order_by(Product.name.asc(), Warehouse.code.asc())
    rows = db.execute(q).all()
    out: list[StockItemOut] = []
    for r in rows:
        out.append(
            StockItemOut(
                id=str(r[0]),
                product_id=str(r[1]),
                warehouse_id=str(r[2]),
                qty=float(r[3] or 0),
                product={
                    "codigo": r[4],
                    "nombre": r[5],
                    "precio": float(r[6] or 0),
                    **(
                        {}
                        if r[7] is None
                        else {
                            "product_metadata": r[7],
                            "metadata": r[7],
                            "stock_minimo": (r[7] or {}).get("stock_minimo"),
                            "reorder_point": (r[7] or {}).get("reorder_point"),
                        }
                    ),
                },
                warehouse={
                    "code": r[8],
                    "name": r[9],
                },
            )
        )
    return out


@router.post("/stock/adjust", response_model=StockItemOut)
def adjust_stock(payload: StockAdjustIn, request: Request, db: Session = Depends(get_db)):
    # Find or create stock item
    tid = _require_tenant_id(request)
    row = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tid,
            StockItem.warehouse_id == payload.warehouse_id,
            StockItem.product_id == payload.product_id,
        )
        .first()
    )
    if not row:
        row = StockItem(
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            qty=0,
            tenant_id=tid,
        )
        db.add(row)
        db.flush()

    qty_abs = abs(payload.delta)
    qty_dec = _dec(qty_abs)
    product = db.query(Product).filter(Product.id == payload.product_id, Product.tenant_id == tid).first()
    fallback_cost = _dec(getattr(product, "cost_price", 0) if product else 0)

    costing = InventoryCostingService(db)
    if payload.delta >= 0:
        unit_cost = _dec(payload.unit_cost) if payload.unit_cost is not None else fallback_cost
        state = costing.apply_inbound(
            tid or "",
            payload.warehouse_id,
            payload.product_id,
            qty=qty_dec,
            unit_cost=unit_cost,
            initial_qty=_dec(row.qty),
            initial_avg_cost=fallback_cost,
        )
    else:
        state = costing.apply_outbound(
            tid or "",
            payload.warehouse_id,
            payload.product_id,
            qty=qty_dec,
            allow_negative=True,
            initial_qty=_dec(row.qty),
            initial_avg_cost=fallback_cost,
        )

    # Create move
    kind = "receipt" if payload.delta >= 0 else "issue"
    unit_cost_for_move = state.avg_cost if payload.delta < 0 else unit_cost
    move = StockMove(
        tenant_id=tid,
        product_id=payload.product_id,
        warehouse_id=payload.warehouse_id,
        qty=qty_abs,
        kind=kind,
        tentative=False,
        ref_type="adjust",
        ref_id=payload.reason or None,
        unit_cost=float(unit_cost_for_move),
        total_cost=float(unit_cost_for_move * qty_dec),
    )
    db.add(move)

    # Update stock qty
    row.qty = (row.qty or 0) + payload.delta
    db.add(row)
    # Persist row + move so aggregation sees latest values
    db.flush()

    # Recalculate aggregated product stock across warehouses (same transaction)
    try:
        from sqlalchemy import func

        total_qty = (
            db.query(func.coalesce(func.sum(StockItem.qty), 0.0))
            .filter(StockItem.product_id == payload.product_id, StockItem.tenant_id == tid)
            .scalar()
        ) or 0.0
        prod = db.query(Product).filter(Product.id == payload.product_id, Product.tenant_id == tid).first()
        if prod:
            prod.stock = float(total_qty)
            db.add(prod)
    except Exception:
        # Non-fatal: keep operation even if sync fails
        pass

    db.commit()
    db.refresh(row)
    return row


class TransferIn(BaseModel):
    from_warehouse_id: str
    to_warehouse_id: str
    product_id: str
    qty: float = Field(gt=0)


@router.post("/stock/transfer", response_model=dict)
def transfer_stock(payload: TransferIn, request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    # Create issue from source and receipt to destination, post atomically
    # Source
    src_item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tid,
            StockItem.warehouse_id == payload.from_warehouse_id,
            StockItem.product_id == payload.product_id,
        )
        .first()
    )
    if not src_item:
        src_item = StockItem(
            warehouse_id=payload.from_warehouse_id,
            product_id=payload.product_id,
            qty=0,
            tenant_id=tid,
        )
        db.add(src_item)
        db.flush()
    if (src_item.qty or 0) < payload.qty:
        raise HTTPException(status_code=400, detail="insufficient_stock")

    # Destination
    dst_item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tid,
            StockItem.warehouse_id == payload.to_warehouse_id,
            StockItem.product_id == payload.product_id,
        )
        .first()
    )
    if not dst_item:
        dst_item = StockItem(
            warehouse_id=payload.to_warehouse_id,
            product_id=payload.product_id,
            qty=0,
            tenant_id=tid,
        )
        db.add(dst_item)
        db.flush()

    qty_dec = _dec(payload.qty)
    product = db.query(Product).filter(Product.id == payload.product_id, Product.tenant_id == tid).first()
    fallback_cost = _dec(getattr(product, "cost_price", 0) if product else 0)

    costing = InventoryCostingService(db)
    state_src = costing.apply_outbound(
        tid or "",
        payload.from_warehouse_id,
        payload.product_id,
        qty=qty_dec,
        allow_negative=False,
        initial_qty=_dec(src_item.qty),
        initial_avg_cost=fallback_cost,
    )
    costing.apply_inbound(
        tid or "",
        payload.to_warehouse_id,
        payload.product_id,
        qty=qty_dec,
        unit_cost=state_src.avg_cost,
        initial_qty=_dec(dst_item.qty),
        initial_avg_cost=state_src.avg_cost,
    )

    # Moves
    mv_issue = StockMove(
        tenant_id=tid,
        product_id=payload.product_id,
        warehouse_id=payload.from_warehouse_id,
        qty=payload.qty,
        kind="issue",
        tentative=False,
        posted=True,
        ref_type="transfer",
        unit_cost=float(state_src.avg_cost),
        total_cost=float(state_src.avg_cost * qty_dec),
    )
    mv_receipt = StockMove(
        tenant_id=tid,
        product_id=payload.product_id,
        warehouse_id=payload.to_warehouse_id,
        qty=payload.qty,
        kind="receipt",
        tentative=False,
        posted=True,
        ref_type="transfer",
        unit_cost=float(state_src.avg_cost),
        total_cost=float(state_src.avg_cost * qty_dec),
    )
    db.add(mv_issue)
    db.add(mv_receipt)

    # Update stock atomically
    src_item.qty = (src_item.qty or 0) - payload.qty
    dst_item.qty = (dst_item.qty or 0) + payload.qty
    db.add(src_item)
    db.add(dst_item)
    # Flush to persist changes before aggregation
    db.flush()

    # Recalculate aggregated product stock after transfer
    try:
        from sqlalchemy import func

        total_qty = (
            db.query(func.coalesce(func.sum(StockItem.qty), 0.0))
            .filter(StockItem.product_id == payload.product_id, StockItem.tenant_id == tid)
            .scalar()
        ) or 0.0
        prod = db.query(Product).filter(Product.id == payload.product_id, Product.tenant_id == tid).first()
        if prod:
            prod.stock = float(total_qty)
            db.add(prod)
    except Exception:
        pass

    db.commit()
    return {"status": "ok", "moved": payload.qty}


class CycleCountIn(BaseModel):
    warehouse_id: str
    product_id: str
    counted_qty: float = Field(ge=0)


@router.post("/stock/cycle_count", response_model=StockItemOut)
def cycle_count(payload: CycleCountIn, request: Request, db: Session = Depends(get_db)):
    tid = _require_tenant_id(request)
    item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == tid,
            StockItem.warehouse_id == payload.warehouse_id,
            StockItem.product_id == payload.product_id,
        )
        .first()
    )
    if not item:
        item = StockItem(
            warehouse_id=payload.warehouse_id,
            product_id=payload.product_id,
            qty=0,
            tenant_id=tid,
        )
        db.add(item)
        db.flush()
    current = float(item.qty or 0)
    delta = float(payload.counted_qty) - current
    if delta != 0:
        qty_dec = _dec(abs(delta))
        product = db.query(Product).filter(Product.id == payload.product_id, Product.tenant_id == tid).first()
        fallback_cost = _dec(getattr(product, "cost_price", 0) if product else 0)
        costing = InventoryCostingService(db)

        if delta > 0:
            state = costing.apply_inbound(
                tid or "",
                str(payload.warehouse_id),
                str(payload.product_id),
                qty=qty_dec,
                unit_cost=fallback_cost,
                initial_qty=_dec(item.qty),
                initial_avg_cost=fallback_cost,
            )
        else:
            state = costing.apply_outbound(
                tid or "",
                str(payload.warehouse_id),
                str(payload.product_id),
                qty=qty_dec,
                allow_negative=True,
                initial_qty=_dec(item.qty),
                initial_avg_cost=fallback_cost,
            )

        # create adjust move posted
        unit_cost_for_move = fallback_cost if delta > 0 else state.avg_cost
        move = StockMove(
            tenant_id=tid,
            product_id=payload.product_id,
            warehouse_id=payload.warehouse_id,
            qty=abs(delta),
            kind=("receipt" if delta > 0 else "issue"),
            tentative=False,
            posted=True,
            ref_type="cycle_count",
            ref_id=str(payload.counted_qty),
            unit_cost=float(unit_cost_for_move),
            total_cost=float(unit_cost_for_move * qty_dec),
        )
        db.add(move)
        item.qty = current + delta
        db.add(item)
    db.commit()
    db.refresh(item)
    return item



class ReorderPointIn(BaseModel):
    stock_minimo: float = Field(ge=0)


@router.post("/products/{product_id}/reorder-point", response_model=dict)
def set_reorder_point(
    product_id: str, payload: ReorderPointIn, request: Request, db: Session = Depends(get_db)
):
    tid = _require_tenant_id(request)
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.tenant_id == tid)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="product_not_found")

    meta = product.product_metadata or {}
    if not isinstance(meta, dict):
        meta = {}
    value = float(payload.stock_minimo)
    meta["stock_minimo"] = value
    meta["reorder_point"] = value
    product.product_metadata = meta
    db.add(product)
    db.commit()

    return {
        "status": "ok",
        "product_id": str(product.id),
        "stock_minimo": float(payload.stock_minimo),
    }


# ============================================================================
# ALERTS CONFIGURATION
# ============================================================================


class AlertConfigIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True
    alert_type: str = Field(default="low_stock")
    threshold_type: str = Field(default="fixed")  # fixed, percentage
    threshold_value: float = Field(gt=0)
    warehouse_ids: list[str] = Field(default_factory=list)
    category_ids: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    notify_email: bool = False
    email_recipients: list[str] = Field(default_factory=list)
    notify_whatsapp: bool = False
    whatsapp_numbers: list[str] = Field(default_factory=list)
    notify_telegram: bool = False
    telegram_chat_ids: list[str] = Field(default_factory=list)
    check_frequency_minutes: int = Field(default=60, ge=15)
    cooldown_hours: int = Field(default=24, ge=1)
    max_alerts_per_day: int = Field(default=10, ge=1)


class AlertConfigOut(BaseModel):
    id: str
    name: str
    is_active: bool
    alert_type: str
    threshold_type: str
    threshold_value: float
    warehouse_ids: list[str]
    category_ids: list[str]
    product_ids: list[str]
    notify_email: bool
    email_recipients: list[str]
    notify_whatsapp: bool
    whatsapp_numbers: list[str]
    notify_telegram: bool
    telegram_chat_ids: list[str]
    check_frequency_minutes: int
    cooldown_hours: int
    max_alerts_per_day: int
    last_checked_at: str | None
    next_check_at: str | None
    created_at: str
    updated_at: str


class AlertHistoryOut(BaseModel):
    id: str
    alert_config_id: str
    product_id: str
    warehouse_id: str | None
    alert_type: str
    threshold_value: float
    current_stock: float
    message: str
    channels_sent: list[str]
    sent_at: str


@router.get("/alerts/configs", response_model=list[AlertConfigOut])
def list_alert_configs(request: Request, db: Session = Depends(get_db)):
    """Lista configuraciones de alertas de inventario"""
    tid = _require_tenant_id(request)
    try:
        from app.models.inventory.alerts import AlertConfig  # Import here to avoid circular imports
    except ImportError:
        return []

    q = select(AlertConfig)
    if tid:
        q = q.where(AlertConfig.tenant_id == tid)
    q = q.order_by(AlertConfig.created_at.desc())
    rows = db.execute(q).scalars().all()

    return [
        AlertConfigOut(
            id=str(r.id),
            name=r.name,
            is_active=r.is_active,
            alert_type=r.alert_type,
            threshold_type=r.threshold_type,
            threshold_value=float(r.threshold_value),
            warehouse_ids=r.warehouse_ids or [],
            category_ids=r.category_ids or [],
            product_ids=r.product_ids or [],
            notify_email=r.notify_email,
            email_recipients=r.email_recipients or [],
            notify_whatsapp=r.notify_whatsapp,
            whatsapp_numbers=r.whatsapp_numbers or [],
            notify_telegram=r.notify_telegram,
            telegram_chat_ids=r.telegram_chat_ids or [],
            check_frequency_minutes=r.check_frequency_minutes,
            cooldown_hours=r.cooldown_hours,
            max_alerts_per_day=r.max_alerts_per_day,
            last_checked_at=r.last_checked_at.isoformat() if r.last_checked_at else None,
            next_check_at=r.next_check_at.isoformat() if r.next_check_at else None,
            created_at=r.created_at.isoformat(),
            updated_at=r.updated_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/alerts/configs", response_model=AlertConfigOut, status_code=201)
def create_alert_config(payload: AlertConfigIn, request: Request, db: Session = Depends(get_db)):
    """Crea una nueva configuración de alertas"""
    tid = _require_tenant_id(request)
    try:
        from app.models.inventory.alerts import AlertConfig
    except ImportError:
        raise HTTPException(status_code=500, detail="Alert models not available")

    # Calculate next check time
    next_check = datetime.utcnow() + timedelta(minutes=payload.check_frequency_minutes)

    config = AlertConfig(
        tenant_id=tid,
        name=payload.name,
        is_active=payload.is_active,
        alert_type=payload.alert_type,
        threshold_type=payload.threshold_type,
        threshold_value=payload.threshold_value,
        warehouse_ids=payload.warehouse_ids,
        category_ids=payload.category_ids,
        product_ids=payload.product_ids,
        notify_email=payload.notify_email,
        email_recipients=payload.email_recipients,
        notify_whatsapp=payload.notify_whatsapp,
        whatsapp_numbers=payload.whatsapp_numbers,
        notify_telegram=payload.notify_telegram,
        telegram_chat_ids=payload.telegram_chat_ids,
        check_frequency_minutes=payload.check_frequency_minutes,
        cooldown_hours=payload.cooldown_hours,
        max_alerts_per_day=payload.max_alerts_per_day,
        next_check_at=next_check,
    )

    db.add(config)
    db.commit()
    db.refresh(config)

    return AlertConfigOut(
        id=str(config.id),
        name=config.name,
        is_active=config.is_active,
        alert_type=config.alert_type,
        threshold_type=config.threshold_type,
        threshold_value=float(config.threshold_value),
        warehouse_ids=config.warehouse_ids or [],
        category_ids=config.category_ids or [],
        product_ids=config.product_ids or [],
        notify_email=config.notify_email,
        email_recipients=config.email_recipients or [],
        notify_whatsapp=config.notify_whatsapp,
        whatsapp_numbers=config.whatsapp_numbers or [],
        notify_telegram=config.notify_telegram,
        telegram_chat_ids=config.telegram_chat_ids or [],
        check_frequency_minutes=config.check_frequency_minutes,
        cooldown_hours=config.cooldown_hours,
        max_alerts_per_day=config.max_alerts_per_day,
        last_checked_at=config.last_checked_at.isoformat() if config.last_checked_at else None,
        next_check_at=config.next_check_at.isoformat() if config.next_check_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.put("/alerts/configs/{config_id}", response_model=AlertConfigOut)
def update_alert_config(
    config_id: str, payload: AlertConfigIn, request: Request, db: Session = Depends(get_db)
):
    """Actualiza una configuración de alertas"""
    tid = _require_tenant_id(request)
    try:
        from app.models.inventory.alerts import AlertConfig
    except ImportError:
        raise HTTPException(status_code=500, detail="Alert models not available")

    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    if tid and str(config.tenant_id) != tid:
        raise HTTPException(status_code=404, detail="Alert config not found")

    # Update fields
    for field, value in payload.model_dump().items():
        setattr(config, field, value)

    # Recalculate next check time
    config.next_check_at = datetime.utcnow() + timedelta(minutes=config.check_frequency_minutes)

    db.add(config)
    db.commit()
    db.refresh(config)

    return AlertConfigOut(
        id=str(config.id),
        name=config.name,
        is_active=config.is_active,
        alert_type=config.alert_type,
        threshold_type=config.threshold_type,
        threshold_value=float(config.threshold_value),
        warehouse_ids=config.warehouse_ids or [],
        category_ids=config.category_ids or [],
        product_ids=config.product_ids or [],
        notify_email=config.notify_email,
        email_recipients=config.email_recipients or [],
        notify_whatsapp=config.notify_whatsapp,
        whatsapp_numbers=config.whatsapp_numbers or [],
        notify_telegram=config.notify_telegram,
        telegram_chat_ids=config.telegram_chat_ids or [],
        check_frequency_minutes=config.check_frequency_minutes,
        cooldown_hours=config.cooldown_hours,
        max_alerts_per_day=config.max_alerts_per_day,
        last_checked_at=config.last_checked_at.isoformat() if config.last_checked_at else None,
        next_check_at=config.next_check_at.isoformat() if config.next_check_at else None,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/alerts/configs/{config_id}", status_code=204)
def delete_alert_config(config_id: str, request: Request, db: Session = Depends(get_db)):
    """Elimina una configuración de alertas"""
    tid = _require_tenant_id(request)
    try:
        from app.models.inventory.alerts import AlertConfig
    except ImportError:
        return

    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        return
    if tid and str(config.tenant_id) != tid:
        return

    db.delete(config)
    db.commit()
    return


@router.post("/alerts/test/{config_id}")
def test_alert_config(config_id: str, request: Request, db: Session = Depends(get_db)):
    """Envía una alerta de prueba para la configuración especificada"""
    tid = _require_tenant_id(request)
    try:
        from app.models.inventory.alerts import AlertConfig
        from app.services.notifications import NotificationService
    except ImportError:
        raise HTTPException(status_code=500, detail="Alert or notification services not available")

    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Alert config not found")
    if tid and str(config.tenant_id) != tid:
        raise HTTPException(status_code=404, detail="Alert config not found")

    # Send test notification
    notification_service = NotificationService(db)
    test_message = f"🔔 ALERTA DE PRUEBA - {config.name}\n\nEsta es una notificación de prueba del sistema de alertas de inventario."

    channels_sent = []
    errors = []

    try:
        if config.notify_email and config.email_recipients:
            notification_service.send_email(
                recipients=config.email_recipients,
                subject=f"Test Alert: {config.name}",
                body=test_message,
            )
            channels_sent.append("email")
    except Exception as e:
        errors.append(f"Email error: {str(e)}")

    try:
        if config.notify_whatsapp and config.whatsapp_numbers:
            for number in config.whatsapp_numbers:
                notification_service.send_whatsapp(number, test_message)
            channels_sent.append("whatsapp")
    except Exception as e:
        errors.append(f"WhatsApp error: {str(e)}")

    try:
        if config.notify_telegram and config.telegram_chat_ids:
            for chat_id in config.telegram_chat_ids:
                notification_service.send_telegram(chat_id, test_message)
            channels_sent.append("telegram")
    except Exception as e:
        errors.append(f"Telegram error: {str(e)}")

    return {
        "status": "test_sent",
        "channels_sent": channels_sent,
        "errors": errors if errors else None,
    }


@router.post("/alerts/check")
def check_alerts(request: Request, db: Session = Depends(get_db)):
    """Ejecuta verificación manual de alertas (para testing)"""
    tid = _require_tenant_id(request)
    try:
        from app.services.inventory_alerts import InventoryAlertService
    except ImportError:
        raise HTTPException(status_code=500, detail="Alert service not available")

    alert_service = InventoryAlertService(db)
    results = alert_service.check_and_send_alerts(tenant_id=tid)

    return {
        "status": "checked",
        "alerts_sent": len(results.get("alerts_sent", [])),
        "errors": results.get("errors", []),
    }


@router.get("/alerts/history", response_model=list[AlertHistoryOut])
def list_alert_history(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, le=200),
    days_back: int = Query(default=7, le=90),
):
    """Lista el historial de alertas enviadas"""
    tid = _require_tenant_id(request)
    since_date = datetime.utcnow() - timedelta(days=days_back)

    try:
        from app.models.inventory.alerts import AlertHistory
    except ImportError:
        return []

    q = select(AlertHistory).where(AlertHistory.sent_at >= since_date)
    if tid:
        q = q.where(AlertHistory.tenant_id == tid)
    q = q.order_by(AlertHistory.sent_at.desc()).limit(limit)
    rows = db.execute(q).scalars().all()

    return [
        AlertHistoryOut(
            id=str(r.id),
            alert_config_id=str(r.alert_config_id),
            product_id=str(r.product_id),
            warehouse_id=str(r.warehouse_id) if r.warehouse_id else None,
            alert_type=r.alert_type,
            threshold_value=float(r.threshold_value),
            current_stock=float(r.current_stock),
            message=r.message,
            channels_sent=r.channels_sent or [],
            sent_at=r.sent_at.isoformat(),
        )
        for r in rows
    ]
