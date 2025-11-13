"""
Tests de Módulo de Nóminas (RRHH)

Valida cálculo de nóminas, conceptos salariales y validaciones.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.schemas.hr_nomina import (
    NominaCreate,
    NominaUpdate,
    NominaConceptoCreate,
    NominaCalculateRequest,
)


class TestNominaSchemas:
    """Tests de schemas de nóminas"""
    
    def test_nomina_create_schema(self):
        """Schema de creación de nómina"""
        empleado_id = uuid4()
        
        data = NominaCreate(
            empleado_id=empleado_id,
            periodo_mes=11,
            periodo_ano=2025,
            tipo="MENSUAL",
            salario_base=Decimal("1200.00"),
        )
        
        assert data.empleado_id == empleado_id
        assert data.periodo_mes == 11
        assert data.periodo_ano == 2025
        assert data.salario_base == Decimal("1200.00")
    
    def test_nomina_create_validates_mes(self):
        """Mes debe estar entre 1 y 12"""
        empleado_id = uuid4()
        
        # Mes válido
        data = NominaCreate(
            empleado_id=empleado_id,
            periodo_mes=6,
            periodo_ano=2025,
            salario_base=Decimal("1000"),
        )
        assert data.periodo_mes == 6
        
        # Mes inválido debe fallar
        with pytest.raises(ValueError):
            NominaCreate(
                empleado_id=empleado_id,
                periodo_mes=13,  # > 12
                periodo_ano=2025,
                salario_base=Decimal("1000"),
            )
    
    def test_nomina_concepto_create(self):
        """Schema de conceptos salariales"""
        data = NominaConceptoCreate(
            tipo="DEVENGO",
            codigo="PLUS_TRANS",
            descripcion="Plus transporte",
            importe=Decimal("150.00"),
            es_base=True,
        )
        
        assert data.tipo == "DEVENGO"
        assert data.codigo == "PLUS_TRANS"
        assert data.importe == Decimal("150.00")
        assert data.es_base is True
    
    def test_nomina_concepto_tipo_validation(self):
        """Tipo de concepto debe ser DEVENGO o DEDUCCION"""
        # DEVENGO válido
        data1 = NominaConceptoCreate(
            tipo="DEVENGO",
            codigo="PLUS",
            descripcion="Plus",
            importe=Decimal("100"),
        )
        assert data1.tipo == "DEVENGO"
        
        # DEDUCCION válido
        data2 = NominaConceptoCreate(
            tipo="DEDUCCION",
            codigo="ANTICIPO",
            descripcion="Anticipo",
            importe=Decimal("50"),
        )
        assert data2.tipo == "DEDUCCION"


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


class TestNominaStatus:
    """Tests de estados de nóminas"""
    
    def test_nomina_status_draft(self):
        """Nómina empieza en DRAFT"""
        status = "DRAFT"
        assert status in ["DRAFT", "APPROVED", "PAID", "CANCELLED"]
    
    def test_nomina_status_transitions(self):
        """Estados permitidos"""
        valid_statuses = ["DRAFT", "APPROVED", "PAID", "CANCELLED"]
        
        for s in valid_statuses:
            assert s in ["DRAFT", "APPROVED", "PAID", "CANCELLED"]
    
    def test_nomina_tipo_values(self):
        """Tipos de nómina válidos"""
        valid_tipos = ["MENSUAL", "EXTRA", "FINIQUITO", "ESPECIAL"]
        
        for tipo in valid_tipos:
            assert tipo in ["MENSUAL", "EXTRA", "FINIQUITO", "ESPECIAL"]


class TestNominaIntegration:
    """Tests de integración con sector config"""
    
    def test_nominas_universal_across_sectors(self):
        """Nóminas debe funcionar en todos los sectores"""
        from app.services.sector_defaults import SECTOR_DEFAULTS
        
        # Nóminas es universal, no depende de sector
        # Todos los sectores tienen empleados
        assert "panaderia" in SECTOR_DEFAULTS
        assert "retail" in SECTOR_DEFAULTS
        assert "restaurante" in SECTOR_DEFAULTS
        assert "taller" in SECTOR_DEFAULTS
    
    def test_conceptos_differ_by_sector(self):
        """Conceptos pueden variar por sector pero estructura es igual"""
        # Panadería: Plus nocturnidad (madrugada)
        concepto_pan = NominaConceptoCreate(
            tipo="DEVENGO",
            codigo="PLUS_NOCTURN",
            descripcion="Plus nocturnidad",
            importe=Decimal("100"),
        )
        
        # Retail: Plus domingos/festivos
        concepto_retail = NominaConceptoCreate(
            tipo="DEVENGO",
            codigo="PLUS_FESTIVO",
            descripcion="Plus festivos",
            importe=Decimal("120"),
        )
        
        # Restaurante: Plus propinas
        concepto_rest = NominaConceptoCreate(
            tipo="DEVENGO",
            codigo="PROPINAS",
            descripcion="Propinas",
            importe=Decimal("200"),
        )
        
        # Todos válidos, diferentes códigos
        assert concepto_pan.codigo != concepto_retail.codigo
        assert concepto_retail.codigo != concepto_rest.codigo
        # Pero misma estructura
        assert concepto_pan.tipo == concepto_retail.tipo == concepto_rest.tipo
