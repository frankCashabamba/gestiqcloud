from __future__ import annotations

from uuid import uuid4

import pytest


def test_panaderia_dashboard_separates_sale_products_and_raw_materials(db):
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("Postgres-specific analytics query test")

    from app.models.core.products import Product
    from app.models.inventory.stock import StockItem
    from app.models.inventory.warehouse import Warehouse
    from app.models.tenant import Tenant
    from app.modules.analytics.interface.http.tenant import _sector_kpis_payload

    tenant = Tenant(
        id=uuid4(),
        name="Panaderia KPIs",
        slug="panaderia-kpis",
        sector_template_name="panaderia",
    )
    warehouse = Warehouse(
        id=uuid4(),
        tenant_id=tenant.id,
        code="MAIN",
        name="Principal",
        is_active=True,
    )
    sale_product = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="PAN-001",
        name="Pan frances",
        active=True,
        stock=0,
        unit="uds",
        price=1,
        is_raw_material=False,
    )
    raw_material = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="HAR-001",
        name="Harina",
        active=True,
        stock=0,
        unit="kg",
        price=0,
        is_raw_material=True,
    )
    healthy_product = Product(
        id=uuid4(),
        tenant_id=tenant.id,
        sku="GAL-001",
        name="Galleta",
        active=True,
        stock=0,
        unit="uds",
        price=1,
        is_raw_material=False,
    )
    db.add_all([tenant, warehouse, sale_product, raw_material, healthy_product])
    db.commit()

    db.add_all(
        [
            StockItem(
                id=uuid4(),
                tenant_id=tenant.id,
                warehouse_id=warehouse.id,
                product_id=sale_product.id,
                qty=2,
            ),
            StockItem(
                id=uuid4(),
                tenant_id=tenant.id,
                warehouse_id=warehouse.id,
                product_id=raw_material.id,
                qty=3,
            ),
            StockItem(
                id=uuid4(),
                tenant_id=tenant.id,
                warehouse_id=warehouse.id,
                product_id=healthy_product.id,
                qty=50,
            ),
        ]
    )
    db.commit()

    payload = _sector_kpis_payload("panaderia", str(tenant.id), db, "USD")
    critical_stock = payload["critical_stock"]

    assert critical_stock["items"] == 2
    assert critical_stock["sale_products"]["items"] == 1
    assert critical_stock["sale_products"]["names"] == ["Pan frances"]
    assert critical_stock["raw_materials"]["items"] == 1
    assert critical_stock["raw_materials"]["names"] == ["Harina"]
