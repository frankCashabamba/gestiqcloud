from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4


def _request_for_tenant(tenant_id: str):
    return SimpleNamespace(
        state=SimpleNamespace(access_claims={"tenant_id": tenant_id})
    )


def test_adjust_stock_persists_lot_and_expiry(db):
    from app.models.core.products import Product
    from app.models.inventory.stock import InventoryCostState, StockItem, StockMove
    from app.models.inventory.warehouse import Warehouse
    from app.models.tenant import Tenant
    from app.modules.inventory.interface.http.tenant import (
        StockAdjustIn,
        adjust_stock,
        get_stock,
    )

    bind = db.get_bind()
    StockItem.__table__.create(bind=bind, checkfirst=True)
    StockMove.__table__.create(bind=bind, checkfirst=True)
    InventoryCostState.__table__.create(bind=bind, checkfirst=True)

    tenant = Tenant(id=uuid4(), name="Inventory Tenant", slug=f"inv-{uuid4().hex[:8]}")
    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=tenant.id,
        code="MAIN",
        name="Main Warehouse",
        is_active=True,
    )
    product = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="PAN-001",
        name="Pan del dia",
        active=True,
        stock=0,
        unit="unit",
    )
    db.add_all([tenant, warehouse, product])
    db.commit()

    request = _request_for_tenant(str(tenant.id))
    payload = StockAdjustIn(
        warehouse_id=str(warehouse.id),
        product_id=str(product.id),
        delta=12,
        reason="purchase",
        lote="LOT-20260312-001",
        expires_at=date(2026, 3, 20),
    )

    result = adjust_stock(payload, request, db)

    assert result.lote == "LOT-20260312-001"
    assert result.expires_at == "2026-03-20"

    stock_item = (
        db.query(StockItem)
        .filter(
            StockItem.tenant_id == str(tenant.id),
            StockItem.warehouse_id == str(warehouse.id),
            StockItem.product_id == str(product.id),
        )
        .first()
    )
    assert stock_item is not None
    assert stock_item.lot == "LOT-20260312-001"
    assert stock_item.expires_at == date(2026, 3, 20)

    stock_move = (
        db.query(StockMove)
        .filter(
            StockMove.tenant_id == str(tenant.id),
            StockMove.warehouse_id == str(warehouse.id),
            StockMove.product_id == str(product.id),
            StockMove.kind == "receipt",
        )
        .first()
    )
    assert stock_move is not None
    assert stock_move.lot == "LOT-20260312-001"
    assert stock_move.expires_at == date(2026, 3, 20)

    rows = get_stock(
        request,
        db,
        warehouse_id=str(warehouse.id),
        product_id=str(product.id),
    )
    assert len(rows) == 1
    assert rows[0].lote == "LOT-20260312-001"
    assert rows[0].expires_at == "2026-03-20"
