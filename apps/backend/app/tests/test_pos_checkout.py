"""
C-T1: Tests unitarios para los Use Cases del POS.

Cubre:
- OpenShiftUseCase: validaciones de register activo y turno ya abierto
- CreateReceiptUseCase: cálculo de totales con descuentos e IVA
- CheckoutReceiptUseCase: validación de pagos y cálculo de cambio
- CloseShiftUseCase: resumen de ventas y varianza de caja
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.modules.pos.application.use_cases import (
    CheckoutReceiptUseCase,
    CloseShiftUseCase,
    CreateReceiptUseCase,
    OpenShiftUseCase,
)


def _make_db(rows: dict | None = None):
    """Crea un mock de Session con respuestas configurables por clave."""
    db = MagicMock()
    calls = {"count": 0, "rows": list(rows.values()) if rows else []}

    def _execute_side_effect(stmt, params=None):
        result = MagicMock()
        idx = calls["count"]
        calls["count"] += 1
        row = calls["rows"][idx] if idx < len(calls["rows"]) else None
        result.first.return_value = row
        result.fetchall.return_value = [row] if row else []
        result.scalar.return_value = row[0] if row and hasattr(row, "__getitem__") else None
        return result

    db.execute.side_effect = _execute_side_effect
    return db


# ============================================================================
# OpenShiftUseCase
# ============================================================================


class TestOpenShiftUseCase:

    def test_raises_when_register_not_found(self):
        db = MagicMock()
        # register query returns None
        db.execute.return_value.first.return_value = None

        uc = OpenShiftUseCase(db)
        with pytest.raises(ValueError, match="register_not_found"):
            uc.execute(
                register_id=uuid.uuid4(),
                opening_float=Decimal("100"),
                cashier_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_raises_when_register_inactive(self):
        db = MagicMock()
        # register row: active=False
        db.execute.return_value.first.return_value = (False,)

        uc = OpenShiftUseCase(db)
        with pytest.raises(ValueError, match="register_inactive"):
            uc.execute(
                register_id=uuid.uuid4(),
                opening_float=Decimal("50"),
                cashier_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_raises_when_shift_already_open(self):
        db = MagicMock()
        call_count = {"n": 0}
        shift_id = uuid.uuid4()

        def execute_side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                # register: active=True
                result.first.return_value = (True,)
            else:
                # existing open shift found
                result.first.return_value = (shift_id,)
            return result

        db.execute.side_effect = execute_side

        uc = OpenShiftUseCase(db)
        with pytest.raises(ValueError, match="shift_already_open"):
            uc.execute(
                register_id=uuid.uuid4(),
                opening_float=Decimal("100"),
                cashier_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_raises_on_negative_opening_float(self):
        db = MagicMock()
        uc = OpenShiftUseCase(db)
        with pytest.raises(ValueError, match="negativo"):
            uc.execute(
                register_id=uuid.uuid4(),
                opening_float=Decimal("-1"),
                cashier_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_opens_shift_successfully(self):
        db = MagicMock()
        new_shift_id = uuid.uuid4()
        register_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        call_count = {"n": 0}

        def execute_side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                result.first.return_value = (True,)   # register active
            elif n == 1:
                result.first.return_value = None       # no open shift
            else:
                result.first.return_value = (new_shift_id,)  # INSERT RETURNING
            return result

        db.execute.side_effect = execute_side

        uc = OpenShiftUseCase(db)
        result = uc.execute(
            register_id=register_id,
            opening_float=Decimal("200"),
            cashier_id=cashier_id,
            tenant_id=tenant_id,
        )

        assert result["shift_id"] == new_shift_id
        assert result["status"] == "open"
        assert result["opening_float"] == Decimal("200")


# ============================================================================
# CreateReceiptUseCase
# ============================================================================


class TestCreateReceiptUseCase:

    def test_raises_when_shift_not_found(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None

        uc = CreateReceiptUseCase(db)
        with pytest.raises(ValueError, match="shift_not_found"):
            uc.execute(
                register_id=uuid.uuid4(),
                shift_id=uuid.uuid4(),
                lines=[],
                tenant_id=uuid.uuid4(),
                cashier_id=uuid.uuid4(),
            )

    def test_raises_when_shift_not_open(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = ("closed",)

        uc = CreateReceiptUseCase(db)
        with pytest.raises(ValueError, match="shift_not_open"):
            uc.execute(
                register_id=uuid.uuid4(),
                shift_id=uuid.uuid4(),
                lines=[],
                tenant_id=uuid.uuid4(),
                cashier_id=uuid.uuid4(),
            )

    def test_calculates_totals_correctly(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = ("open",)

        uc = CreateReceiptUseCase(db)
        lines = [
            {"product_id": str(uuid.uuid4()), "qty": "2", "unit_price": "10.00",
             "discount_pct": "10", "tax_rate": "0.12"},
            {"product_id": str(uuid.uuid4()), "qty": "1", "unit_price": "50.00",
             "discount_pct": "0", "tax_rate": "0.12"},
        ]

        result = uc.execute(
            register_id=uuid.uuid4(),
            shift_id=uuid.uuid4(),
            lines=lines,
            tenant_id=uuid.uuid4(),
            cashier_id=uuid.uuid4(),
        )

        # line1: 2 * 10 * 0.90 = 18.00, tax = 18 * 0.12 = 2.16
        # line2: 1 * 50 * 1.00 = 50.00, tax = 50 * 0.12 = 6.00
        # subtotal = 68.00, tax = 8.16, total = 76.16
        assert result["status"] == "draft"
        assert result["subtotal"] == Decimal("68.00")
        assert result["tax"] == pytest.approx(Decimal("8.16"), abs=Decimal("0.01"))
        assert result["total"] == pytest.approx(Decimal("76.16"), abs=Decimal("0.01"))

    def test_empty_lines_gives_zero_totals(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = ("open",)

        uc = CreateReceiptUseCase(db)
        result = uc.execute(
            register_id=uuid.uuid4(),
            shift_id=uuid.uuid4(),
            lines=[],
            tenant_id=uuid.uuid4(),
            cashier_id=uuid.uuid4(),
        )

        assert result["subtotal"] == Decimal("0")
        assert result["tax"] == Decimal("0")
        assert result["total"] == Decimal("0")


# ============================================================================
# CheckoutReceiptUseCase
# ============================================================================


class TestCheckoutReceiptUseCase:

    def _make_checkout_db(self, receipt_status="draft", subtotal=100.0, tax=12.0):
        """Configura el mock de DB para el flujo de checkout."""
        db = MagicMock()
        call_count = {"n": 0}

        def execute_side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                # receipt row: (shift_id, status, gross_total)
                result.first.return_value = (uuid.uuid4(), receipt_status, subtotal + tax)
            elif n == 1:
                # lines
                result.fetchall.return_value = [
                    (uuid.uuid4(), uuid.uuid4(), Decimal("2"), Decimal("50"), Decimal("0"))
                ]
            else:
                # totals: (subtotal, tax)
                result.first.return_value = (subtotal, tax)
            return result

        db.execute.side_effect = execute_side
        return db

    def test_raises_when_receipt_not_found(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None

        uc = CheckoutReceiptUseCase(db, costing_service=MagicMock())
        with pytest.raises(ValueError, match="receipt_not_found"):
            uc.execute(
                receipt_id=uuid.uuid4(),
                payments=[{"amount": "100"}],
                warehouse_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_raises_when_receipt_not_draft(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = (uuid.uuid4(), "paid", Decimal("100"))

        uc = CheckoutReceiptUseCase(db, costing_service=MagicMock())
        with pytest.raises(ValueError, match="invalid_status:paid"):
            uc.execute(
                receipt_id=uuid.uuid4(),
                payments=[{"amount": "100"}],
                warehouse_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
            )

    def test_calculates_change_correctly(self):
        db = self._make_checkout_db(subtotal=100.0, tax=12.0)

        uc = CheckoutReceiptUseCase(db, costing_service=MagicMock())
        result = uc.execute(
            receipt_id=uuid.uuid4(),
            payments=[{"amount": "150"}],  # paga 150, total=112
            warehouse_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
        )

        assert result["status"] == "paid"
        assert result["total"] == Decimal("112")
        assert result["change"] == Decimal("38")  # 150 - 112

    def test_no_change_when_exact_payment(self):
        db = self._make_checkout_db(subtotal=100.0, tax=0.0)

        uc = CheckoutReceiptUseCase(db, costing_service=MagicMock())
        result = uc.execute(
            receipt_id=uuid.uuid4(),
            payments=[{"amount": "100"}],
            warehouse_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
        )

        assert result["change"] == Decimal("0")


# ============================================================================
# CloseShiftUseCase
# ============================================================================


class TestCloseShiftUseCase:

    def test_raises_when_shift_not_found(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = None

        uc = CloseShiftUseCase(db)
        with pytest.raises(ValueError, match="shift_not_found"):
            uc.execute(
                shift_id=uuid.uuid4(),
                cash_count=Decimal("100"),
                tenant_id=uuid.uuid4(),
            )

    def test_raises_when_shift_already_closed(self):
        db = MagicMock()
        db.execute.return_value.first.return_value = ("closed", uuid.uuid4(), Decimal("100"))

        uc = CloseShiftUseCase(db)
        with pytest.raises(ValueError, match="shift_already_closed"):
            uc.execute(
                shift_id=uuid.uuid4(),
                cash_count=Decimal("100"),
                tenant_id=uuid.uuid4(),
            )

    def test_calculates_variance_correctly(self):
        db = MagicMock()
        call_count = {"n": 0}

        def execute_side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                # shift: (status, register_id, opening_float)
                result.first.return_value = ("open", uuid.uuid4(), Decimal("100"))
            else:
                # sales: (method, amount) — efectivo=200
                result.fetchall.return_value = [("cash", Decimal("200"))]
            return result

        db.execute.side_effect = execute_side

        uc = CloseShiftUseCase(db)
        result = uc.execute(
            shift_id=uuid.uuid4(),
            cash_count=Decimal("290"),  # esperado: 100+200=300, variance=-10
            tenant_id=uuid.uuid4(),
        )

        assert result["status"] == "closed"
        assert result["expected_cash"] == Decimal("300")   # opening_float + cash_sales
        assert result["variance"] == Decimal("-10")         # 290 - 300
        assert result["sales_total"] == Decimal("200")

    def test_zero_variance_when_exact_count(self):
        db = MagicMock()
        call_count = {"n": 0}

        def execute_side(stmt, params=None):
            result = MagicMock()
            n = call_count["n"]
            call_count["n"] += 1
            if n == 0:
                result.first.return_value = ("open", uuid.uuid4(), Decimal("50"))
            else:
                result.fetchall.return_value = [("cash", Decimal("450"))]
            return result

        db.execute.side_effect = execute_side

        uc = CloseShiftUseCase(db)
        result = uc.execute(
            shift_id=uuid.uuid4(),
            cash_count=Decimal("500"),
            tenant_id=uuid.uuid4(),
        )

        assert result["variance"] == Decimal("0")
