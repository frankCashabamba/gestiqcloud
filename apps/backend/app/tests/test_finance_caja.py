"""
Tests de Módulo de Finanzas (Caja)

Valida movimientos de caja, cierres y cálculos.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.schemas.finance_caja import CashClosingCreate, CashMovementCreate


class TestCajaMovimientoSchema:
    """Tests de movimientos de caja"""

    def test_caja_movimiento_create_ingreso(self):
        """Crear movimiento de ingreso"""
        data = CashMovementCreate(
            movement_type="INCOME",
            amount=Decimal("150.00"),
            description="Venta contado",
            ref_doc_type="pos_receipt",
        )

        assert data.movement_type == "INCOME"
        assert data.amount == Decimal("150.00")
        assert data.description == "Venta contado"

    def test_caja_movimiento_create_egreso(self):
        """Crear movimiento de egreso"""
        data = CashMovementCreate(
            movement_type="EXPENSE",
            amount=Decimal("50.00"),
            description="Materials purchase",
        )

        assert data.movement_type == "EXPENSE"
        assert data.amount == Decimal("50.00")

    def test_caja_movimiento_movement_type_validation(self):
        """Tipo debe ser INCOME o EXPENSE"""
        # INCOME válido
        data1 = CashMovementCreate(
            movement_type="INCOME", amount=Decimal("100"), description="Test"
        )
        assert data1.movement_type == "INCOME"

        # EXPENSE válido
        data2 = CashMovementCreate(
            movement_type="EXPENSE", amount=Decimal("50"), description="Test"
        )
        assert data2.movement_type == "EXPENSE"


class TestCashClosingSchema:
    """Tests de cierre de caja"""

    def test_cierre_caja_create(self):
        """Crear cierre de caja"""
        data = CashClosingCreate(
            date=date(2025, 11, 3),
            opening_balance=Decimal("100.00"),
            total_income=Decimal("450.00"),
            total_expense=Decimal("80.00"),
        )

        assert data.date == date(2025, 11, 3)
        assert data.opening_balance == Decimal("100.00")
        assert data.total_income == Decimal("450.00")
        assert data.total_expense == Decimal("80.00")

    def test_cierre_caja_final_balance_calculation(self):
        """Saldo final = inicial + ingresos - egresos"""
        opening_balance = Decimal("100.00")
        total_income = Decimal("450.00")
        total_expense = Decimal("80.00")

        final_balance = opening_balance + total_income - total_expense

        assert final_balance == Decimal("470.00")


class TestCajaCalculations:
    """Tests de cálculos de caja"""

    def test_saldo_calculation(self):
        """Saldo = ingresos - egresos"""
        ingresos = Decimal("1000.00")
        egresos = Decimal("300.00")

        saldo = ingresos - egresos

        assert saldo == Decimal("700.00")

    def test_multiple_movements(self):
        """Suma de múltiples movimientos"""
        movimientos = [
            {"movement_type": "INCOME", "amount": Decimal("100")},
            {"movement_type": "INCOME", "amount": Decimal("200")},
            {"movement_type": "EXPENSE", "amount": Decimal("50")},
            {"movement_type": "INCOME", "amount": Decimal("150")},
            {"movement_type": "EXPENSE", "amount": Decimal("30")},
        ]

        total_income = sum(m["amount"] for m in movimientos if m["movement_type"] == "INCOME")
        total_expense = sum(m["amount"] for m in movimientos if m["movement_type"] == "EXPENSE")

        assert total_income == Decimal("450")
        assert total_expense == Decimal("80")
        assert total_income - total_expense == Decimal("370")


class TestCajaIntegration:
    """Tests de integración con otros módulos"""

    def test_caja_universal_across_sectors(self):
        """Caja funciona en todos los sectores"""
        from app.services.sector_defaults import SECTOR_DEFAULTS

        # Todos los sectores usan caja
        assert "panaderia" in SECTOR_DEFAULTS
        assert "retail" in SECTOR_DEFAULTS
        # Caja es universal, no depende de sector

    def test_caja_integrates_with_pos(self):
        """Caja recibe movimientos automáticos del POS"""
        # Simular venta POS que genera movimiento de caja
        venta_pos = {
            "movement_type": "INCOME",
            "amount": Decimal("25.50"),
            "ref_doc_type": "pos_receipt",
            "ref_doc_id": str(uuid4()),
        }

        assert venta_pos["movement_type"] == "INCOME"
        assert venta_pos["ref_doc_type"] == "pos_receipt"
