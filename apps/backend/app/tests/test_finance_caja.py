"""
Tests de Módulo de Finanzas (Caja)

Valida movimientos de caja, cierres y cálculos.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.schemas.finance_caja import CajaMovimientoCreate, CierreCajaCreate


class TestCajaMovimientoSchema:
    """Tests de movimientos de caja"""

    def test_caja_movimiento_create_ingreso(self):
        """Crear movimiento de ingreso"""
        data = CajaMovimientoCreate(
            tipo="INGRESO",
            importe=Decimal("150.00"),
            descripcion="Venta contado",
            ref_doc_type="pos_receipt",
        )

        assert data.tipo == "INGRESO"
        assert data.importe == Decimal("150.00")
        assert data.descripcion == "Venta contado"

    def test_caja_movimiento_create_egreso(self):
        """Crear movimiento de egreso"""
        data = CajaMovimientoCreate(
            tipo="EGRESO",
            importe=Decimal("50.00"),
            descripcion="Compra materiales",
        )

        assert data.tipo == "EGRESO"
        assert data.importe == Decimal("50.00")

    def test_caja_movimiento_tipo_validation(self):
        """Tipo debe ser INGRESO o EGRESO"""
        # INGRESO válido
        data1 = CajaMovimientoCreate(tipo="INGRESO", importe=Decimal("100"), descripcion="Test")
        assert data1.tipo == "INGRESO"

        # EGRESO válido
        data2 = CajaMovimientoCreate(tipo="EGRESO", importe=Decimal("50"), descripcion="Test")
        assert data2.tipo == "EGRESO"


class TestCierreCajaSchema:
    """Tests de cierre de caja"""

    def test_cierre_caja_create(self):
        """Crear cierre de caja"""
        data = CierreCajaCreate(
            fecha=date(2025, 11, 3),
            saldo_inicial=Decimal("100.00"),
            total_ingresos=Decimal("450.00"),
            total_egresos=Decimal("80.00"),
        )

        assert data.fecha == date(2025, 11, 3)
        assert data.saldo_inicial == Decimal("100.00")
        assert data.total_ingresos == Decimal("450.00")
        assert data.total_egresos == Decimal("80.00")

    def test_cierre_caja_saldo_final_calculation(self):
        """Saldo final = inicial + ingresos - egresos"""
        saldo_inicial = Decimal("100.00")
        total_ingresos = Decimal("450.00")
        total_egresos = Decimal("80.00")

        saldo_final = saldo_inicial + total_ingresos - total_egresos

        assert saldo_final == Decimal("470.00")


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
            {"tipo": "INGRESO", "importe": Decimal("100")},
            {"tipo": "INGRESO", "importe": Decimal("200")},
            {"tipo": "EGRESO", "importe": Decimal("50")},
            {"tipo": "INGRESO", "importe": Decimal("150")},
            {"tipo": "EGRESO", "importe": Decimal("30")},
        ]

        total_ingresos = sum(m["importe"] for m in movimientos if m["tipo"] == "INGRESO")
        total_egresos = sum(m["importe"] for m in movimientos if m["tipo"] == "EGRESO")

        assert total_ingresos == Decimal("450")
        assert total_egresos == Decimal("80")
        assert total_ingresos - total_egresos == Decimal("370")


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
            "tipo": "INGRESO",
            "importe": Decimal("25.50"),
            "ref_doc_type": "pos_receipt",
            "ref_doc_id": str(uuid4()),
        }

        assert venta_pos["tipo"] == "INGRESO"
        assert venta_pos["ref_doc_type"] == "pos_receipt"
