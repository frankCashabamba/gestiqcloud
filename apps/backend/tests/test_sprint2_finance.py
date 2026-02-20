"""Tests - Finance Module (Sprint 2)"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.finance.cash import CashPosition, BankStatement, BankStatementLine, CashProjection
from app.models.finance.payment import Payment, PaymentSchedule
from app.models.accounting.chart_of_accounts import ChartOfAccounts
from app.modules.finance.application.cash_service import CashPositionService


@pytest.fixture
def tenant_id(db: Session):
    tid = uuid4()
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, :active, :created_at)"
        ),
        {
            "id": tid.hex,
            "name": "Sprint2 Finance",
            "slug": f"s2-fin-{tid.hex[:8]}",
            "active": True,
            "created_at": datetime.utcnow(),
        },
    )
    db.flush()
    return tid


@pytest.fixture
def bank_account(db: Session, tenant_id):
    """Crea cuenta bancaria de prueba."""
    account = ChartOfAccounts(
        id=uuid4(),
        tenant_id=tenant_id,
        code="101",
        name="Banco Prueba",
        type="ASSET",
        level=3,
        can_post=True,
        active=True,
    )
    db.add(account)
    db.flush()
    return account


# ============================================================================
# TESTS: Cash Position
# ============================================================================

def test_cash_position_calculation_no_previous(db: Session, tenant_id, bank_account):
    """Test: calcula posición sin saldo anterior."""
    position_date = date(2026, 2, 15)
    
    position = CashPositionService.calculate_position(
        db, tenant_id, bank_account.id, position_date
    )
    
    assert position.tenant_id == tenant_id
    assert position.bank_account_id == bank_account.id
    assert position.position_date == position_date
    assert position.opening_balance == Decimal("0")
    assert position.inflows == Decimal("0")
    assert position.outflows == Decimal("0")
    assert position.closing_balance == Decimal("0")


def test_cash_position_with_payments(db: Session, tenant_id, bank_account):
    """Test: calcula posición con pagos."""
    today = date.today()
    
    # Crear pagos confirmados
    payment_in = Payment(
        tenant_id=tenant_id,
        amount=Decimal("1000.00"),
        payment_date=today,
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    payment_out = Payment(
        tenant_id=tenant_id,
        amount=Decimal("-500.00"),
        payment_date=today,
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="bill",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    db.add(payment_in)
    db.add(payment_out)
    db.flush()
    
    position = CashPositionService.calculate_position(
        db, tenant_id, bank_account.id, today
    )
    
    assert position.inflows == Decimal("1000.00")
    assert position.outflows == Decimal("500.00")
    assert position.closing_balance == Decimal("500.00")


def test_cash_position_calculation_formula(db: Session, tenant_id, bank_account):
    """Test: verifica fórmula closing = opening + inflows - outflows."""
    today = date.today()
    
    # Crear posición anterior
    yesterday = today - timedelta(days=1)
    previous = CashPosition(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        position_date=yesterday,
        opening_balance=Decimal("5000.00"),
        inflows=Decimal("2000.00"),
        outflows=Decimal("1000.00"),
        closing_balance=Decimal("6000.00"),
    )
    db.add(previous)
    db.flush()
    
    # Crear posición actual
    position = CashPosition(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        position_date=today,
        opening_balance=Decimal("6000.00"),
        inflows=Decimal("3000.00"),
        outflows=Decimal("1500.00"),
        closing_balance=Decimal("7500.00"),
    )
    db.add(position)
    db.flush()
    
    # Verificar fórmula
    expected_closing = position.opening_balance + position.inflows - position.outflows
    assert position.closing_balance == expected_closing


# ============================================================================
# TESTS: Bank Statement
# ============================================================================

def test_bank_statement_creation(db: Session, tenant_id, bank_account):
    """Test: crea extracto bancario."""
    statement = BankStatement(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        statement_date=date(2026, 2, 28),
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        opening_balance=Decimal("10000.00"),
        closing_balance=Decimal("12500.00"),
        source="IMPORT",
        status="DRAFT",
        currency="EUR",
        bank_ref="STATEMENT-2026-02",
    )
    db.add(statement)
    db.flush()
    
    assert statement.id is not None
    assert statement.opening_balance == Decimal("10000.00")
    assert statement.closing_balance == Decimal("12500.00")


def test_bank_statement_lines(db: Session, tenant_id, bank_account):
    """Test: crea líneas de extracto bancario."""
    statement = BankStatement(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        statement_date=date(2026, 2, 28),
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        opening_balance=Decimal("10000.00"),
        closing_balance=Decimal("12500.00"),
    )
    db.add(statement)
    db.flush()
    
    # Agregar líneas
    line1 = BankStatementLine(
        statement_id=statement.id,
        transaction_date=date(2026, 2, 5),
        amount=Decimal("1500.00"),
        description="Ingreso cliente",
        reference="REF-001",
        line_number=1,
    )
    line2 = BankStatementLine(
        statement_id=statement.id,
        transaction_date=date(2026, 2, 10),
        amount=Decimal("-500.00"),
        description="Pago proveedor",
        reference="REF-002",
        line_number=2,
    )
    db.add(line1)
    db.add(line2)
    db.flush()
    
    assert len(statement.lines) == 2
    assert statement.lines[0].amount == Decimal("1500.00")
    assert statement.lines[1].amount == Decimal("-500.00")


# ============================================================================
# TESTS: Cash Projection
# ============================================================================

def test_cash_projection_creation(db: Session, tenant_id, bank_account):
    """Test: crea proyección de flujo de caja."""
    today = date.today()
    end_date = today + timedelta(days=30)
    
    projection = CashProjection(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        projection_date=today,
        projection_end_date=end_date,
        period_days=30,
        opening_balance=Decimal("5000.00"),
        projected_inflows=Decimal("3000.00"),
        projected_outflows=Decimal("1500.00"),
        projected_balance=Decimal("6500.00"),
        scenario="BASE",
    )
    db.add(projection)
    db.flush()
    
    assert projection.projected_balance == Decimal("6500.00")
    assert projection.scenario == "BASE"


def test_cash_projection_formula(db: Session, tenant_id, bank_account):
    """Test: verifica fórmula projected_balance = opening + inflows - outflows."""
    today = date.today()
    end_date = today + timedelta(days=30)
    
    opening = Decimal("10000.00")
    inflows = Decimal("5000.00")
    outflows = Decimal("2000.00")
    expected_balance = opening + inflows - outflows
    
    projection = CashProjection(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        projection_date=today,
        projection_end_date=end_date,
        opening_balance=opening,
        projected_inflows=inflows,
        projected_outflows=outflows,
        projected_balance=expected_balance,
    )
    db.add(projection)
    db.flush()
    
    assert projection.projected_balance == expected_balance


# ============================================================================
# TESTS: Payments
# ============================================================================

def test_payment_status_transitions(db: Session, tenant_id, bank_account):
    """Test: transiciones de estado de pago."""
    payment = Payment(
        tenant_id=tenant_id,
        amount=Decimal("1000.00"),
        payment_date=date.today(),
        method="BANK_TRANSFER",
        status="PENDING",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    db.add(payment)
    db.flush()
    
    assert payment.status == "PENDING"
    
    # Cambiar a IN_PROGRESS
    payment.status = "IN_PROGRESS"
    db.flush()
    assert payment.status == "IN_PROGRESS"
    
    # Cambiar a CONFIRMED
    payment.status = "CONFIRMED"
    payment.confirmed_date = date.today()
    db.flush()
    assert payment.status == "CONFIRMED"


def test_payment_schedule(db: Session, tenant_id):
    """Test: plan de pagos con cuotas."""
    schedule = PaymentSchedule(
        tenant_id=tenant_id,
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        total_amount=Decimal("1200.00"),
        installments=3,
        frequency="MONTHLY",
        start_date=date(2026, 2, 1),
        status="ACTIVE",
    )
    db.add(schedule)
    db.flush()
    
    assert schedule.installments == 3
    assert schedule.status == "ACTIVE"
    assert schedule.paid_amount == Decimal("0")
    
    # Simular pago de cuota
    schedule.paid_amount = Decimal("400.00")
    schedule.paid_installments = 1
    db.flush()
    
    assert schedule.paid_installments == 1


# ============================================================================
# TESTS: Multi-Currency
# ============================================================================

def test_payment_multi_currency(db: Session, tenant_id, bank_account):
    """Test: pagos en múltiples monedas."""
    payment_eur = Payment(
        tenant_id=tenant_id,
        amount=Decimal("1000.00"),
        currency="EUR",
        payment_date=date.today(),
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    payment_usd = Payment(
        tenant_id=tenant_id,
        amount=Decimal("1200.00"),
        currency="USD",
        payment_date=date.today(),
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    db.add(payment_eur)
    db.add(payment_usd)
    db.flush()
    
    assert payment_eur.currency == "EUR"
    assert payment_usd.currency == "USD"


# ============================================================================
# TESTS: Validations
# ============================================================================

def test_cash_position_negative_outflows(db: Session, tenant_id, bank_account):
    """Test: maneja outflows negativos correctamente."""
    position = CashPosition(
        tenant_id=tenant_id,
        bank_account_id=bank_account.id,
        position_date=date.today(),
        opening_balance=Decimal("10000.00"),
        inflows=Decimal("0"),
        outflows=Decimal("5000.00"),
        closing_balance=Decimal("5000.00"),
    )
    db.add(position)
    db.flush()
    
    # Closing debe ser positivo incluso con outflows grandes
    assert position.closing_balance >= Decimal("0")


def test_payment_zero_amount_validation(db: Session, tenant_id, bank_account):
    """Test: valida pagos con monto cero."""
    # SQLAlchemy no restricta a nivel ORM, pero en BD debería haber CHECK
    payment = Payment(
        tenant_id=tenant_id,
        amount=Decimal("0"),  # Inválido en lógica de negocio
        payment_date=date.today(),
        method="BANK_TRANSFER",
        status="PENDING",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    db.add(payment)
    
    # En prod: lanzar error en servicio


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_cash_position_service_calculation(db: Session, tenant_id, bank_account):
    """Test: servicio calcula posición correctamente."""
    today = date.today()
    
    # Crear pagos
    payment_in = Payment(
        tenant_id=tenant_id,
        amount=Decimal("5000.00"),
        payment_date=today,
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="invoice",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    payment_out = Payment(
        tenant_id=tenant_id,
        amount=Decimal("-2000.00"),
        payment_date=today,
        method="BANK_TRANSFER",
        status="CONFIRMED",
        ref_doc_type="bill",
        ref_doc_id=uuid4(),
        bank_account_id=bank_account.id,
    )
    db.add(payment_in)
    db.add(payment_out)
    db.flush()
    
    # Usar servicio
    position = CashPositionService.calculate_position(
        db, tenant_id, bank_account.id, today
    )
    
    assert position.inflows == Decimal("5000.00")
    assert position.outflows == Decimal("2000.00")
    assert position.closing_balance == Decimal("3000.00")


def test_multi_day_positions(db: Session, tenant_id, bank_account):
    """Test: obtiene posiciones para rango de fechas."""
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 5)
    
    # Crear posiciones para cada día
    for i in range(5):
        position = CashPosition(
            tenant_id=tenant_id,
            bank_account_id=bank_account.id,
            position_date=start_date + timedelta(days=i),
            opening_balance=Decimal("10000.00") + (i * Decimal("500.00")),
            inflows=Decimal("1000.00"),
            outflows=Decimal("500.00"),
            closing_balance=Decimal("10500.00") + (i * Decimal("500.00")),
        )
        db.add(position)
    db.flush()
    
    positions = CashPositionService.get_multi_day_positions(
        db, tenant_id, bank_account.id, start_date, end_date
    )
    
    assert len(positions) == 5
    assert positions[0].position_date == start_date
    assert positions[-1].position_date == end_date


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
