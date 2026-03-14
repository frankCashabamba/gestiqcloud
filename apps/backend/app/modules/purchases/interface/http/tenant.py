from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.inventory.stock import StockItem, StockMove
from app.models.purchases.purchase import PurchaseLine
from app.modules.settings.infrastructure.repositories import SettingsRepo
from app.services.inventory_costing import InventoryCostingService

from ...infrastructure.repositories import PurchaseRepo
from .schemas import PurchaseCreate, PurchaseOut, PurchaseUpdate

router = APIRouter(
    prefix="/purchases",
    tags=["Purchases"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


@router.get("", response_model=list[PurchaseOut])
def list_purchases(db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)):
    tenant_id = claims["tenant_id"]
    return PurchaseRepo(db).list(tenant_id)


@router.get("/{cid}", response_model=PurchaseOut)
def get_purchase(
    cid: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    obj = PurchaseRepo(db).get(tenant_id, cid)
    if not obj:
        raise HTTPException(404, "Not found")
    return obj


@router.post("", response_model=PurchaseOut)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    return PurchaseRepo(db).create(tenant_id, **payload.model_dump())


@router.put("/{cid}", response_model=PurchaseOut)
def update_purchase(
    cid: UUID,
    payload: PurchaseUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    try:
        return PurchaseRepo(db).update(tenant_id, cid, **payload.model_dump())
    except ValueError:
        raise HTTPException(404, "Not found")


@router.delete("/{cid}")
def delete_purchase(
    cid: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    try:
        PurchaseRepo(db).delete(tenant_id, cid)
    except ValueError:
        raise HTTPException(404, "Not found")
    return {"success": True}


def _dec(value: float | Decimal | None, q: str = "0.000001") -> Decimal:
    if value is None:
        value = 0
    return Decimal(str(value)).quantize(Decimal(q), rounding=ROUND_HALF_UP)


def _normalize_lot(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_inventory_costing_method(db: Session) -> str:
    try:
        repo = SettingsRepo(db)
        inventory_cfg = repo.get("inventory") or {}
        method = (
            str(
                (inventory_cfg.get("costing_method") if isinstance(inventory_cfg, dict) else None)
                or "avg"
            )
            .strip()
            .lower()
        )
        return method if method in {"avg", "fifo", "lifo"} else "avg"
    except Exception:
        return "avg"


class PurchaseReceiveLineIn(BaseModel):
    product_id: UUID
    qty: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    lote: str | None = None
    expires_at: date | None = None


class PurchaseReceiveIn(BaseModel):
    warehouse_id: UUID
    lines: list[PurchaseReceiveLineIn] = Field(min_length=1)


@router.post("/{cid}/receive", response_model=dict)
def receive_purchase(
    cid: UUID,
    payload: PurchaseReceiveIn,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    purchase = PurchaseRepo(db).get(tenant_id, cid)
    if not purchase:
        raise HTTPException(404, "Not found")

    costing = InventoryCostingService(db)
    costing_method = _resolve_inventory_costing_method(db)
    for line in payload.lines:
        qty_dec = _dec(line.qty)
        unit_cost_dec = _dec(line.unit_cost)
        line_lot = _normalize_lot(line.lote)

        # Update stock item with lock
        row = (
            db.query(StockItem)
            .filter(
                StockItem.tenant_id == str(tenant_id),
                StockItem.warehouse_id == str(payload.warehouse_id),
                StockItem.product_id == str(line.product_id),
                StockItem.lot == line_lot if line_lot is not None else StockItem.lot.is_(None),
                (
                    StockItem.expires_at == line.expires_at
                    if line.expires_at is not None
                    else StockItem.expires_at.is_(None)
                ),
            )
            .with_for_update()
            .first()
        )
        if not row:
            row = StockItem(
                tenant_id=str(tenant_id),
                warehouse_id=str(payload.warehouse_id),
                product_id=str(line.product_id),
                qty=0,
                lot=line_lot,
                expires_at=line.expires_at,
            )
            db.add(row)
            db.flush()

        if costing_method == "fifo":
            costing.apply_inbound_fifo(
                str(tenant_id),
                str(payload.warehouse_id),
                str(line.product_id),
                qty=qty_dec,
                unit_cost=unit_cost_dec,
                lot=line_lot,
                expires_at=line.expires_at,
            )
        elif costing_method == "lifo":
            costing.apply_inbound_lifo(
                str(tenant_id),
                str(payload.warehouse_id),
                str(line.product_id),
                qty=qty_dec,
                unit_cost=unit_cost_dec,
                lot=line_lot,
                expires_at=line.expires_at,
            )
        else:
            costing.apply_inbound(
                str(tenant_id),
                str(payload.warehouse_id),
                str(line.product_id),
                qty=qty_dec,
                unit_cost=unit_cost_dec,
                initial_qty=_dec(row.qty),
                initial_avg_cost=unit_cost_dec,
            )

        row.qty = (row.qty or 0) + float(qty_dec)
        db.add(row)

        db.add(
            StockMove(
                tenant_id=str(tenant_id),
                product_id=str(line.product_id),
                warehouse_id=str(payload.warehouse_id),
                qty=float(qty_dec),
                kind="receipt",
                tentative=False,
                posted=True,
                ref_type="purchase",
                ref_id=str(purchase.id),
                lot=line_lot,
                expires_at=line.expires_at,
                unit_cost=float(unit_cost_dec),
                total_cost=float(unit_cost_dec * qty_dec),
            )
        )

        db.add(
            PurchaseLine(
                purchase_id=purchase.id,
                product_id=line.product_id,
                description=None,
                quantity=float(qty_dec),
                unit_price=float(unit_cost_dec),
                tax_rate=0,
                total=float(unit_cost_dec * qty_dec),
            )
        )

    purchase.status = "received"
    db.add(purchase)
    db.commit()
    return {"ok": True, "purchase_id": str(purchase.id), "status": "received"}
