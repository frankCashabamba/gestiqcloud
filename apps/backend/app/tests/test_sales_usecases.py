"""Tests for Sales module schemas and logic."""

import pytest
from decimal import Decimal

pytestmark = pytest.mark.no_db

from app.modules.sales.application.schemas import SalesOrderLineModel


class TestSalesOrderLineModel:
    def test_line_subtotal_no_discount(self):
        line = SalesOrderLineModel(
            product_id="00000000-0000-0000-0000-000000000001",
            product_name="Widget",
            qty=Decimal("3"),
            unit_price=Decimal("10.00"),
            discount_pct=Decimal("0"),
        )
        assert line.line_subtotal == Decimal("30.00")

    def test_line_subtotal_with_discount(self):
        line = SalesOrderLineModel(
            product_id="00000000-0000-0000-0000-000000000001",
            product_name="Widget",
            qty=Decimal("2"),
            unit_price=Decimal("100.00"),
            discount_pct=Decimal("10"),
        )
        # 2 * 100 * (1 - 10/100) = 180
        assert line.line_subtotal == Decimal("180.00")

    def test_line_total_includes_tax(self):
        line = SalesOrderLineModel(
            product_id="00000000-0000-0000-0000-000000000001",
            product_name="Widget",
            qty=Decimal("1"),
            unit_price=Decimal("100.00"),
            discount_pct=Decimal("0"),
        )
        # 100 * 1.21 = 121
        assert line.line_total == Decimal("121.00")

    def test_discount_100_percent(self):
        line = SalesOrderLineModel(
            product_id="00000000-0000-0000-0000-000000000001",
            product_name="Free Widget",
            qty=Decimal("5"),
            unit_price=Decimal("50.00"),
            discount_pct=Decimal("100"),
        )
        assert line.line_subtotal == Decimal("0")

    def test_discount_validation_max_100(self):
        with pytest.raises(Exception):
            SalesOrderLineModel(
                product_id="00000000-0000-0000-0000-000000000001",
                product_name="Widget",
                qty=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount_pct=Decimal("101"),
            )

    def test_negative_discount_rejected(self):
        with pytest.raises(Exception):
            SalesOrderLineModel(
                product_id="00000000-0000-0000-0000-000000000001",
                product_name="Widget",
                qty=Decimal("1"),
                unit_price=Decimal("100.00"),
                discount_pct=Decimal("-5"),
            )

    def test_zero_qty_rejected(self):
        with pytest.raises(Exception):
            SalesOrderLineModel(
                product_id="00000000-0000-0000-0000-000000000001",
                product_name="Widget",
                qty=Decimal("0"),
                unit_price=Decimal("100.00"),
            )

    def test_default_discount_is_zero(self):
        line = SalesOrderLineModel(
            product_id="00000000-0000-0000-0000-000000000001",
            product_name="Widget",
            qty=Decimal("1"),
            unit_price=Decimal("50.00"),
        )
        assert line.discount_pct == Decimal("0")
        assert line.line_subtotal == Decimal("50.00")
