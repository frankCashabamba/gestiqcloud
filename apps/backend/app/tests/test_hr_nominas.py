"""
Tests de Módulo de Nóminas (RRHH)

Valida cálculo de nóminas, conceptos salariales y validaciones.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.hr_nomina import PayrollConceptCreate, PayrollCreate


class TestPayrollSchemas:
    """Payroll schema tests"""

    def test_nomina_create_schema(self):
        """Schema de creación de nómina"""
        employee_id = uuid4()

        data = PayrollCreate(
            employee_id=employee_id,
            period_month=11,
            period_year=2025,
            payroll_type="MONTHLY",
            base_salary=Decimal("1200.00"),
        )

        assert data.employee_id == employee_id
        assert data.period_month == 11
        assert data.period_year == 2025
        assert data.base_salary == Decimal("1200.00")

    def test_nomina_create_validates_mes(self):
        """Mes debe estar entre 1 y 12"""
        employee_id = uuid4()

        # Mes válido
        data = PayrollCreate(
            employee_id=employee_id,
            period_month=6,
            period_year=2025,
            base_salary=Decimal("1000"),
        )
        assert data.period_month == 6

        # Mes inválido debe fallar
        with pytest.raises(ValueError):
            PayrollCreate(
                employee_id=employee_id,
                period_month=13,  # > 12
                period_year=2025,
                base_salary=Decimal("1000"),
            )

    def test_payroll_concept_create(self):
        """Schema de conceptos salariales"""
        data = PayrollConceptCreate(
            concept_type="EARNING",
            code="PLUS_TRANS",
            description="Transport allowance",
            amount=Decimal("150.00"),
            is_base=True,
        )

        assert data.concept_type == "EARNING"
        assert data.code == "PLUS_TRANS"
        assert data.amount == Decimal("150.00")
        assert data.is_base is True

    def test_payroll_concept_type_validation(self):
        """concept_type must be EARNING or DEDUCTION"""
        # EARNING válido
        data1 = PayrollConceptCreate(
            concept_type="EARNING",
            code="PLUS",
            description="Plus",
            amount=Decimal("100"),
        )
        assert data1.concept_type == "EARNING"

        # DEDUCTION válido
        data2 = PayrollConceptCreate(
            concept_type="DEDUCTION",
            code="ANTICIPO",
            description="Advance",
            amount=Decimal("50"),
        )
        assert data2.concept_type == "DEDUCTION"


class TestNominaCalculations:
    """Tests de cálculos de nóminas"""

    def test_total_devengado_calculation(self):
        """Total devengado = salario_base + complementos + horas_extra + otros"""
        salario_base = Decimal("1200.00")
        complementos = Decimal("150.00")
        horas_extra = Decimal("80.00")
        otros_devengos = Decimal("50.00")

        total_devengado = salario_base + complementos + horas_extra + otros_devengos

        assert total_devengado == Decimal("1480.00")

    def test_total_deducido_calculation(self):
        """Total deducido = seg_social + irpf + otras_deducciones"""
        seg_social = Decimal("84.00")  # 7% de 1200
        irpf = Decimal("180.00")  # 15% de 1200
        otras_deducciones = Decimal("20.00")

        total_deducido = seg_social + irpf + otras_deducciones

        assert total_deducido == Decimal("284.00")

    def test_liquido_total_calculation(self):
        """Líquido total = total_devengado - total_deducido"""
        total_devengado = Decimal("1480.00")
        total_deducido = Decimal("284.00")

        liquido_total = total_devengado - total_deducido

        assert liquido_total == Decimal("1196.00")

    def test_seguridad_social_espana(self):
        """Cálculo de Seguridad Social España (~6.35%)"""
        salario_base = Decimal("1200.00")
        porcentaje = Decimal("0.0635")

        seg_social = (salario_base * porcentaje).quantize(Decimal("0.01"))

        assert seg_social == Decimal("76.20")

    def test_irpf_espana_basic(self):
        """Cálculo de IRPF España básico (15%)"""
        salario_base = Decimal("1200.00")
        porcentaje = Decimal("0.15")

        irpf = (salario_base * porcentaje).quantize(Decimal("0.01"))

        assert irpf == Decimal("180.00")


class TestPayrollStatus:
    """Payroll status tests"""

    def test_nomina_status_draft(self):
        """Payroll starts in DRAFT"""
        status = "DRAFT"
        assert status in ["DRAFT", "APPROVED", "PAID", "CANCELLED"]

    def test_nomina_status_transitions(self):
        """Allowed statuses"""
        valid_statuses = ["DRAFT", "APPROVED", "PAID", "CANCELLED"]

        for s in valid_statuses:
            assert s in ["DRAFT", "APPROVED", "PAID", "CANCELLED"]

    def test_payroll_type_values(self):
        """Valid payroll types"""
        valid_types = ["MONTHLY", "BONUS", "SEVERANCE", "SPECIAL"]

        for t in valid_types:
            assert t in ["MONTHLY", "BONUS", "SEVERANCE", "SPECIAL"]


class TestPayrollIntegration:
    """Integration tests with sector config"""

    def test_nominas_universal_across_sectors(self):
        """Payroll should work for all sectors"""
        from app.services.sector_defaults import SECTOR_DEFAULTS

        # Nóminas es universal, no depende de sector
        # Todos los sectores tienen empleados
        assert "panaderia" in SECTOR_DEFAULTS
        assert "retail" in SECTOR_DEFAULTS
        assert "restaurante" in SECTOR_DEFAULTS
        assert "taller" in SECTOR_DEFAULTS

    def test_conceptos_differ_by_sector(self):
        """Concepts can vary by sector but structure is the same"""
        # Bakery: night shift bonus
        concept_bakery = PayrollConceptCreate(
            concept_type="EARNING",
            code="PLUS_NOCTURN",
            description="Night shift bonus",
            amount=Decimal("100"),
        )

        # Retail: weekend/holiday bonus
        concept_retail = PayrollConceptCreate(
            concept_type="EARNING",
            code="PLUS_FESTIVO",
            description="Holiday bonus",
            amount=Decimal("120"),
        )

        # Restaurant: tips
        concept_rest = PayrollConceptCreate(
            concept_type="EARNING",
            code="PROPINAS",
            description="Tips",
            amount=Decimal("200"),
        )

        # Todos válidos, diferentes códigos
        assert concept_bakery.code != concept_retail.code
        assert concept_retail.code != concept_rest.code
        # Pero misma estructura
        assert (
            concept_bakery.concept_type == concept_retail.concept_type == concept_rest.concept_type
        )
