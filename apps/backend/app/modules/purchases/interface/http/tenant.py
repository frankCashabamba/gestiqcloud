# DECISION v1: El flujo de aprobación de compras queda fuera del alcance del primer release.
# Las compras pasan directamente de 'draft' a 'received' sin etapa de aprobación formal.
# FASE 2: implementar endpoint POST /{id}/approve con workflow de doble firma.

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.models.core.products import Product
from app.models.inventory.stock import StockItem, StockMove
from app.models.inventory.warehouse import Warehouse
from app.models.purchases.purchase import PurchaseLine
from app.modules.settings.infrastructure.repositories import SettingsRepo
from app.services.inventory_costing import InventoryCostingService
from app.shared.utils import normalize_lot as _normalize_lot
from app.shared.utils import to_decimal as _dec

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
def list_purchases(
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
    supplier_id: UUID | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
):
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="tenant_id_not_found")
    return PurchaseRepo(db).list(
        tenant_id,
        supplier_id=supplier_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=min(limit, 200),
    )


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
    user_id = claims.get("user_id") or claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="user_id_not_found")
    product_ids = [line.product_id for line in payload.lines if line.product_id]
    if product_ids:
        owned_products = {
            str(row[0])
            for row in db.query(Product.id)
            .filter(Product.tenant_id == tenant_id, Product.id.in_(product_ids))
            .all()
        }
        if any(str(product_id) not in owned_products for product_id in product_ids):
            raise HTTPException(status_code=404, detail="product_not_found")
    return PurchaseRepo(db).create(
        tenant_id,
        date=payload.date,
        supplier_id=payload.supplier_id,
        total=payload.total,
        status=payload.status,
        lines=payload.lines,
        subtotal=payload.subtotal,
        taxes=payload.taxes,
        notes=payload.notes,
        delivery_date=payload.delivery_date,
        user_id=user_id,
    )


@router.put("/{cid}", response_model=PurchaseOut)
def update_purchase(
    cid: UUID,
    payload: PurchaseUpdate,
    db: Session = Depends(get_db),
    claims: dict = Depends(with_access_claims),
):
    tenant_id = claims["tenant_id"]
    try:
        return PurchaseRepo(db).update(
            tenant_id,
            cid,
            date=payload.date,
            supplier_id=payload.supplier_id,
            total=payload.total,
            status=payload.status,
        )
    except ValueError:
        raise HTTPException(404, "Not found")


@router.delete("/{cid}")
def delete_purchase(
    cid: UUID, db: Session = Depends(get_db), claims: dict = Depends(with_access_claims)
):
    tenant_id = claims["tenant_id"]
    # Bloquear hard delete si ya hay recepciones o movimientos de stock
    from app.models.inventory.stock import StockMove
    from app.models.purchases.purchase import PurchaseLine as _PL  # noqa: F401

    has_moves = db.query(StockMove.id).filter(StockMove.reference == str(cid)).first()
    if has_moves:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar una compra que ya tiene recepciones o movimientos de stock",
        )
    try:
        PurchaseRepo(db).delete(tenant_id, cid)
    except ValueError:
        raise HTTPException(404, "Not found")
    return {"success": True}


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
    quantity: float = Field(gt=0)
    unit_cost: float = Field(ge=0)
    lot: str | None = None
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

    warehouse = (
        db.query(Warehouse)
        .filter(Warehouse.id == payload.warehouse_id, Warehouse.tenant_id == tenant_id)
        .first()
    )
    if not warehouse:
        raise HTTPException(status_code=404, detail="warehouse_not_found")

    costing = InventoryCostingService(db)
    costing_method = _resolve_inventory_costing_method(db)
    for line in payload.lines:
        product = (
            db.query(Product)
            .filter(Product.id == line.product_id, Product.tenant_id == tenant_id)
            .first()
        )
        if not product:
            raise HTTPException(status_code=404, detail="product_not_found")
        quantity_dec = _dec(line.quantity)
        unit_cost_dec = _dec(line.unit_cost)
        line_lot = _normalize_lot(line.lot)

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
                qty=quantity_dec,
                unit_cost=unit_cost_dec,
                lot=line_lot,
                expires_at=line.expires_at,
            )
        elif costing_method == "lifo":
            costing.apply_inbound_lifo(
                str(tenant_id),
                str(payload.warehouse_id),
                str(line.product_id),
                qty=quantity_dec,
                unit_cost=unit_cost_dec,
                lot=line_lot,
                expires_at=line.expires_at,
            )
        else:
            costing.apply_inbound(
                str(tenant_id),
                str(payload.warehouse_id),
                str(line.product_id),
                qty=quantity_dec,
                unit_cost=unit_cost_dec,
                initial_qty=_dec(row.qty),
                initial_avg_cost=unit_cost_dec,
            )

        row.qty = (row.qty or 0) + float(quantity_dec)
        db.add(row)

        db.add(
            StockMove(
                tenant_id=str(tenant_id),
                product_id=str(line.product_id),
                warehouse_id=str(payload.warehouse_id),
                qty=float(quantity_dec),
                kind="receipt",
                tentative=False,
                posted=True,
                ref_type="purchase",
                ref_id=str(purchase.id),
                lot=line_lot,
                expires_at=line.expires_at,
                unit_cost=float(unit_cost_dec),
                total_cost=float(unit_cost_dec * quantity_dec),
            )
        )

        db.add(
            PurchaseLine(
                purchase_id=purchase.id,
                product_id=line.product_id,
                description=None,
                quantity=float(quantity_dec),
                unit_price=float(unit_cost_dec),
                tax_rate=0,
                total=float(unit_cost_dec * quantity_dec),
            )
        )

    purchase.status = "received"
    db.add(purchase)
    db.commit()
    return {"ok": True, "purchase_id": str(purchase.id), "status": "received"}
