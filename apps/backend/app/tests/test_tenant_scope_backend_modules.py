from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.core.products import Product
from app.models.inventory.warehouse import Warehouse
from app.models.recipes import Recipe
from app.models.tenant import Tenant
from app.modules.inventory.interface.http.tenant import StockAdjustIn, adjust_stock
from app.modules.pos.application.checkout_service import CheckoutService
from app.modules.production.interface.http.tenant import create_production_order
from app.modules.reports.application.recalculation_service import RecalculationService
from app.schemas.production import ProductionOrderCreate


def _create_tenant(db: Session, name: str) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    db.add(
        Tenant(
            id=tenant_id,
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{tenant_id.hex[:8]}",
            base_currency="USD",
        )
    )
    db.commit()
    return tenant_id


def _fake_request(tenant_id: uuid.UUID, user_id: str = "tester") -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(
            tenant_id=tenant_id,
            access_claims={"tenant_id": str(tenant_id), "user_id": user_id},
        )
    )


def _make_product(db: Session, tenant_id: uuid.UUID, name: str) -> Product:
    product = Product(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        stock=0,
        unit="unit",
        active=True,
    )
    db.add(product)
    db.flush()
    return product


def _make_warehouse(db: Session, tenant_id: uuid.UUID, code: str) -> Warehouse:
    warehouse = Warehouse(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        name=f"Warehouse {code}",
        is_active=True,
    )
    db.add(warehouse)
    db.flush()
    return warehouse


def test_inventory_adjust_stock_rejects_foreign_warehouse(db: Session, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    tenant_b = _create_tenant(db, "Inventory Other")
    product = _make_product(db, tenant_a, "Flour")
    foreign_warehouse = _make_warehouse(db, tenant_b, "B1")
    db.commit()

    with pytest.raises(HTTPException) as exc:
        adjust_stock(
            StockAdjustIn(
                warehouse_id=str(foreign_warehouse.id),
                product_id=str(product.id),
                delta=1,
            ),
            _fake_request(tenant_a),
            db,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "warehouse_not_found"


def test_pos_checkout_service_scopes_warehouse_resolution_by_tenant(db: Session, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    tenant_b = _create_tenant(db, "POS Other")
    foreign_warehouse = _make_warehouse(db, tenant_b, "POS-B")
    db.commit()

    service = CheckoutService(db)

    with pytest.raises(ValueError, match="warehouse_not_found"):
        service._resolve_warehouse(tenant_a, uuid.UUID(str(foreign_warehouse.id)))

    with pytest.raises(ValueError, match="no_active_warehouse"):
        service._resolve_warehouse(tenant_a, None)


def test_production_create_order_rejects_foreign_warehouse(db: Session, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    tenant_b = _create_tenant(db, "Production Other")
    product = _make_product(db, tenant_a, "Bread")
    foreign_warehouse = _make_warehouse(db, tenant_b, "PROD-B")
    recipe = Recipe(
        id=uuid.uuid4(),
        tenant_id=tenant_a,
        product_id=product.id,
        name="Bread Recipe",
        yield_qty=10,
        total_cost=Decimal("5"),
        is_active=True,
    )
    db.add(recipe)
    db.commit()

    payload = ProductionOrderCreate(
        recipe_id=recipe.id,
        product_id=product.id,
        warehouse_id=foreign_warehouse.id,
        qty_planned=Decimal("5"),
        lines=[],
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            create_production_order(
                payload,
                db,
                {"tenant_id": str(tenant_a), "user_id": str(uuid.uuid4())},
            )
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "warehouse_not_found"


def test_recalculation_service_ignores_foreign_product_cost_fallback(db: Session, tenant_minimal):
    tenant_a = tenant_minimal["tenant_id"]
    tenant_b = _create_tenant(db, "Reports Other")
    foreign_product = _make_product(db, tenant_b, "Foreign Product")
    foreign_product.cost_price = Decimal("17.50")
    db.add(foreign_product)
    db.commit()

    service = RecalculationService(db)
    cost = service._get_unit_cost(tenant_a, foreign_product.id, date(2026, 4, 3))

    assert cost == Decimal("0")
