"""Tests for RecalculationService — profit snapshots"""

import uuid
from datetime import date
from decimal import Decimal

import app.models.core.products  # noqa: F401
import app.models.core.profit_snapshots  # noqa: F401
import app.models.sales.order  # noqa: F401


class TestRecalculationService:
    def _make_tenant(self, db):
        from app.models.tenant import Tenant

        tid = uuid.uuid4()
        t = Tenant(id=tid, name="Recalc Test", slug=f"recalc-{tid.hex[:8]}")
        db.add(t)
        db.flush()
        return tid

    def _make_product(self, db, tenant_id, name="Test Product", cost_price=10.0, price=20.0):
        from app.models.core.products import Product

        p = Product(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            sku=f"SKU-{uuid.uuid4().hex[:6]}",
            price=price,
            cost_price=cost_price,
            stock=100,
        )
        db.add(p)
        db.flush()
        return p

    def _make_sale(self, db, tenant_id, order_date, product_id, qty=5, unit_price=20.0):
        from app.models.sales.order import SalesOrder, SalesOrderItem

        order_id = uuid.uuid4()
        line_total = qty * unit_price
        order = SalesOrder(
            id=order_id,
            tenant_id=tenant_id,
            number=f"SO-{uuid.uuid4().hex[:8]}",
            order_date=order_date,
            subtotal=line_total,
            tax=0,
            total=line_total,
            status="completed",
        )
        db.add(order)
        db.flush()
        item = SalesOrderItem(
            id=uuid.uuid4(),
            order_id=order_id,
            product_id=product_id,
            qty=qty,
            unit_price=unit_price,
            line_total=line_total,
        )
        db.add(item)
        db.flush()
        return order

    def _svc(self, db):
        from app.modules.reports.application.recalculation_service import RecalculationService

        return RecalculationService(db)

    def test_recalculate_daily_no_sales(self, db):
        tid = self._make_tenant(db)
        svc = self._svc(db)
        snap = svc.recalculate_daily(tid, date(2026, 1, 15))
        db.flush()
        assert snap is not None
        assert float(snap.total_sales) == 0
        assert snap.order_count == 0

    def test_recalculate_daily_with_sales(self, db):
        tid = self._make_tenant(db)
        product = self._make_product(db, tid, cost_price=8.0, price=20.0)
        self._make_sale(db, tid, date(2026, 2, 1), product.id, qty=10, unit_price=20.0)
        svc = self._svc(db)
        snap = svc.recalculate_daily(tid, date(2026, 2, 1))
        db.flush()
        assert float(snap.total_sales) == 200.0  # 10 * 20
        assert snap.order_count == 1
        # COGS = 10 * 8 = 80 (from product.cost_price)
        assert float(snap.total_cogs) == 80.0
        assert float(snap.gross_profit) == 120.0

    def test_recalculate_daily_upserts(self, db):
        tid = self._make_tenant(db)
        product = self._make_product(db, tid, cost_price=5.0)
        self._make_sale(db, tid, date(2026, 3, 1), product.id, qty=2, unit_price=15.0)
        svc = self._svc(db)
        svc.recalculate_daily(tid, date(2026, 3, 1))
        db.flush()
        # Add another sale same day
        self._make_sale(db, tid, date(2026, 3, 1), product.id, qty=3, unit_price=15.0)
        snap2 = svc.recalculate_daily(tid, date(2026, 3, 1))
        db.flush()
        # Should update, not create duplicate
        assert float(snap2.total_sales) == 75.0  # (2+3) * 15
        assert snap2.order_count == 2

    def test_recalculate_creates_product_snapshots(self, db):
        from app.models.core.profit_snapshots import ProductProfitSnapshot

        tid = self._make_tenant(db)
        p1 = self._make_product(db, tid, name="Bread", cost_price=3.0, price=5.0)
        p2 = self._make_product(db, tid, name="Cake", cost_price=10.0, price=25.0)
        self._make_sale(db, tid, date(2026, 4, 1), p1.id, qty=20, unit_price=5.0)
        self._make_sale(db, tid, date(2026, 4, 1), p2.id, qty=5, unit_price=25.0)
        svc = self._svc(db)
        svc.recalculate_daily(tid, date(2026, 4, 1))
        db.flush()
        product_snaps = (
            db.query(ProductProfitSnapshot)
            .filter(
                ProductProfitSnapshot.tenant_id == tid,
                ProductProfitSnapshot.date == date(2026, 4, 1),
            )
            .all()
        )
        assert len(product_snaps) == 2

    def test_recalculate_range(self, db):
        tid = self._make_tenant(db)
        product = self._make_product(db, tid, cost_price=5.0)
        self._make_sale(db, tid, date(2026, 5, 1), product.id, qty=1, unit_price=10.0)
        self._make_sale(db, tid, date(2026, 5, 2), product.id, qty=2, unit_price=10.0)
        svc = self._svc(db)
        results = svc.recalculate_range(tid, date(2026, 5, 1), date(2026, 5, 3))
        db.flush()
        assert len(results) == 3  # 3 days

    def test_get_unit_cost_from_product(self, db):
        tid = self._make_tenant(db)
        product = self._make_product(db, tid, cost_price=7.50)
        svc = self._svc(db)
        cost = svc._get_unit_cost(tid, product.id, date(2026, 1, 1))
        assert cost == Decimal("7.5") or cost == Decimal("7.50")

    def test_get_unit_cost_no_cost_returns_zero(self, db):
        from app.models.core.products import Product

        tid = self._make_tenant(db)
        p = Product(
            id=uuid.uuid4(),
            tenant_id=tid,
            name="No Cost",
            sku="NC-001",
            stock=0,
        )
        db.add(p)
        db.flush()
        svc = self._svc(db)
        cost = svc._get_unit_cost(tid, p.id, date(2026, 1, 1))
        assert cost == Decimal("0")
