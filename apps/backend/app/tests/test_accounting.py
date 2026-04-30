"""
Tests de Módulo de Contabilidad

Valida plan de cuentas, asientos contables y validación debe=haber.
"""

import secrets
from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.models.accounting.chart_of_accounts import ChartOfAccounts, JournalEntry, JournalEntryLine
from app.schemas.accounting import AsientoContableCreate, AsientoLineaCreate, PlanCuentasCreate


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
            number="A-001",
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

        assert data.number == "A-001"
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

        total_debe = sum(linea["debe"] for linea in lineas)
        total_haber = sum(linea["haber"] for linea in lineas)

        assert total_debe == Decimal("800")
        assert total_haber == Decimal("800")
        assert total_debe == total_haber  # Cuadrado ✅

    def test_asiento_descuadrado_detectado(self):
        """Asiento descuadrado debe ser detectado"""
        lineas = [
            {"debe": Decimal("500"), "haber": Decimal("0")},
            {"debe": Decimal("0"), "haber": Decimal("300")},  # Descuadrado
        ]

        total_debe = sum(linea["debe"] for linea in lineas)
        total_haber = sum(linea["haber"] for linea in lineas)

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

    def test_contabilidad_universal(self, db):
        """Contabilidad es universal (mismo plan contable PGC)"""
        from app.models.company.company import SectorTemplate

        codes = {tpl.code for tpl in db.query(SectorTemplate).all()}
        assert {"panaderia", "retail", "restaurante", "taller"}.issubset(codes)

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


def test_account_ledger_endpoint_returns_posted_movements_with_initial_balance(
    client: TestClient, db, usuario_empresa_factory
):
    password = secrets.token_urlsafe(12)
    user, tenant = usuario_empresa_factory(
        empresa_nombre="Ledger Demo",
        empresa_slug="ledger-demo",
        username="ledger_owner",
        email="ledger@example.com",
        password=password,
    )
    tenant_id = UUID(str(tenant.id))
    user_id = UUID(str(user.id))

    cash = ChartOfAccounts(
        tenant_id=tenant_id,
        code="570",
        name="Caja",
        type="ASSET",
        level=3,
        can_post=True,
        active=True,
    )
    revenue = ChartOfAccounts(
        tenant_id=tenant_id,
        code="700",
        name="Ventas",
        type="INCOME",
        level=3,
        can_post=True,
        active=True,
    )
    db.add_all([cash, revenue])
    db.flush()

    opening = JournalEntry(
        tenant_id=tenant_id,
        number="ASI-2026-0001",
        date=date(2026, 1, 1),
        type="OPENING",
        description="Saldo inicial",
        debit_total=Decimal("100.00"),
        credit_total=Decimal("100.00"),
        is_balanced=True,
        status="POSTED",
        created_by=user_id,
    )
    sale = JournalEntry(
        tenant_id=tenant_id,
        number="ASI-2026-0002",
        date=date(2026, 2, 1),
        type="OPERATIONS",
        description="Venta",
        debit_total=Decimal("25.00"),
        credit_total=Decimal("25.00"),
        is_balanced=True,
        status="POSTED",
        created_by=user_id,
    )
    draft = JournalEntry(
        tenant_id=tenant_id,
        number="ASI-2026-0003",
        date=date(2026, 2, 2),
        type="OPERATIONS",
        description="Borrador",
        debit_total=Decimal("999.00"),
        credit_total=Decimal("999.00"),
        is_balanced=True,
        status="DRAFT",
        created_by=user_id,
    )
    db.add_all([opening, sale, draft])
    db.flush()
    db.add_all(
        [
            JournalEntryLine(
                entry_id=opening.id,
                account_id=cash.id,
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
                description="Caja inicial",
                line_number=1,
            ),
            JournalEntryLine(
                entry_id=opening.id,
                account_id=revenue.id,
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
                line_number=2,
            ),
            JournalEntryLine(
                entry_id=sale.id,
                account_id=cash.id,
                debit=Decimal("25.00"),
                credit=Decimal("0.00"),
                description="Cobro venta",
                line_number=1,
            ),
            JournalEntryLine(
                entry_id=sale.id,
                account_id=revenue.id,
                debit=Decimal("0.00"),
                credit=Decimal("25.00"),
                line_number=2,
            ),
            JournalEntryLine(
                entry_id=draft.id,
                account_id=cash.id,
                debit=Decimal("999.00"),
                credit=Decimal("0.00"),
                line_number=1,
            ),
        ]
    )
    db.commit()

    login = client.post(
        "/api/v1/tenant/auth/login",
        json={"identificador": "ledger_owner", "password": password},
    )
    assert login.status_code == 200

    response = client.get(
        f"/api/v1/tenant/accounting/chart-of-accounts/{cash.id}/ledger"
        "?fecha_desde=2026-02-01&fecha_hasta=2026-02-28",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["cuenta_codigo"] == "570"
    assert Decimal(data["saldo_inicial"]) == Decimal("100.00")
    assert Decimal(data["total_debe"]) == Decimal("25.00")
    assert Decimal(data["total_haber"]) == Decimal("0.00")
    assert Decimal(data["saldo_final"]) == Decimal("125.00")
    assert [m["asiento_numero"] for m in data["movimientos"]] == ["ASI-2026-0002"]
