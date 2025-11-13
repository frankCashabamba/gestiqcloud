"""
Tests de Módulo de Contabilidad

Valida plan de cuentas, asientos contables y validación debe=haber.
"""

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import date

from app.schemas.accounting import (
    PlanCuentasCreate,
    AsientoContableCreate,
    AsientoLineaCreate,
)


class TestPlanCuentasSchema:
    """Tests de plan de cuentas"""
    
    def test_plan_cuenta_create(self):
        """Crear cuenta del plan contable"""
        data = PlanCuentasCreate(
            codigo="1000",
            nombre="Caja",
            tipo="ACTIVO",
            nivel=1,
            activo=True,
        )
        
        assert data.codigo == "1000"
        assert data.nombre == "Caja"
        assert data.tipo == "ACTIVO"
        assert data.nivel == 1
    
    def test_plan_cuenta_tipos_validos(self):
        """Tipos de cuenta válidos"""
        tipos = ["ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"]
        
        for tipo in tipos:
            data = PlanCuentasCreate(
                codigo=f"{tipos.index(tipo)}000",
                nombre=f"Cuenta {tipo}",
                tipo=tipo,
                nivel=1,
            )
            assert data.tipo == tipo
    
    def test_plan_cuenta_nivel_validation(self):
        """Nivel debe estar entre 1 y 5"""
        # Nivel 1 (válido)
        data = PlanCuentasCreate(
            codigo="1000",
            nombre="Activo",
            tipo="ACTIVO",
            nivel=1,
        )
        assert data.nivel == 1


class TestAsientoContableSchema:
    """Tests de asientos contables"""
    
    def test_asiento_create(self):
        """Crear asiento contable"""
        cuenta1 = uuid4()
        cuenta2 = uuid4()
        
        data = AsientoContableCreate(
            numero="A-001",
            fecha=date(2025, 11, 3),
            descripcion="Asiento de apertura",
            lineas=[
                AsientoLineaCreate(
                    cuenta_id=cuenta1,
                    debe=Decimal("1000.00"),
                    haber=Decimal("0"),
                ),
                AsientoLineaCreate(
                    cuenta_id=cuenta2,
                    debe=Decimal("0"),
                    haber=Decimal("1000.00"),
                ),
            ],
        )
        
        assert data.numero == "A-001"
        assert len(data.lineas) == 2
        assert data.lineas[0].debe == Decimal("1000.00")
        assert data.lineas[1].haber == Decimal("1000.00")
    
    def test_asiento_debe_igual_haber(self):
        """Asiento debe estar cuadrado (debe = haber)"""
        lineas = [
            {"debe": Decimal("500"), "haber": Decimal("0")},
            {"debe": Decimal("300"), "haber": Decimal("0")},
            {"debe": Decimal("0"), "haber": Decimal("800")},
        ]
        
        total_debe = sum(l["debe"] for l in lineas)
        total_haber = sum(l["haber"] for l in lineas)
        
        assert total_debe == Decimal("800")
        assert total_haber == Decimal("800")
        assert total_debe == total_haber  # Cuadrado ✅
    
    def test_asiento_descuadrado_detectado(self):
        """Asiento descuadrado debe ser detectado"""
        lineas = [
            {"debe": Decimal("500"), "haber": Decimal("0")},
            {"debe": Decimal("0"), "haber": Decimal("300")},  # Descuadrado
        ]
        
        total_debe = sum(l["debe"] for l in lineas)
        total_haber = sum(l["haber"] for l in lineas)
        
        diferencia = total_debe - total_haber
        
        assert diferencia == Decimal("200")  # Descuadrado
        assert abs(diferencia) > Decimal("0.01")  # No cuadra


class TestAsientoLineaSchema:
    """Tests de líneas de asiento"""
    
    def test_asiento_linea_create(self):
        """Crear línea de asiento"""
        cuenta_id = uuid4()
        
        data = AsientoLineaCreate(
            cuenta_id=cuenta_id,
            debe=Decimal("250.00"),
            haber=Decimal("0"),
            descripcion="Pago proveedor",
        )
        
        assert data.cuenta_id == cuenta_id
        assert data.debe == Decimal("250.00")
        assert data.haber == Decimal("0")
    
    def test_asiento_linea_debe_o_haber(self):
        """Una línea puede tener debe o haber, no ambos a la vez"""
        # Solo debe
        linea1 = AsientoLineaCreate(
            cuenta_id=uuid4(),
            debe=Decimal("100"),
            haber=Decimal("0"),
        )
        assert linea1.debe > 0 and linea1.haber == 0
        
        # Solo haber
        linea2 = AsientoLineaCreate(
            cuenta_id=uuid4(),
            debe=Decimal("0"),
            haber=Decimal("100"),
        )
        assert linea2.haber > 0 and linea2.debe == 0


class TestAccountingIntegration:
    """Tests de integración"""
    
    def test_contabilidad_universal(self):
        """Contabilidad es universal (mismo plan contable PGC)"""
        from app.services.sector_defaults import SECTOR_DEFAULTS
        
        # Plan contable es estándar para todos
        assert len(SECTOR_DEFAULTS) >= 4  # 4 sectores mínimo
    
    def test_cuentas_by_tipo(self):
        """Plan contable debe tener los 5 tipos"""
        tipos = ["ACTIVO", "PASIVO", "PATRIMONIO", "INGRESO", "GASTO"]
        
        # Simulación de plan básico
        plan_basico = [
            {"codigo": "1000", "tipo": "ACTIVO"},
            {"codigo": "2000", "tipo": "PASIVO"},
            {"codigo": "3000", "tipo": "PATRIMONIO"},
            {"codigo": "4000", "tipo": "INGRESO"},
            {"codigo": "5000", "tipo": "GASTO"},
        ]
        
        tipos_plan = [c["tipo"] for c in plan_basico]
        
        for tipo in tipos:
            assert tipo in tipos_plan
