"""Tests - HR Module (Sprint 2)"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
from app.models.expenses.expense import Expense
from app.models.hr.attendance import TimeEntry
from app.models.hr.employee import Employee, EmployeeDeduction, EmployeeSalary
from app.models.hr.payroll import PayrollDetail, PayrollTax
from app.models.hr.payslip import PaymentSlip
from app.modules.hr.application.compensation import build_salary_notes
from app.modules.hr.application.payroll_service import PayrollService


@pytest.fixture
def tenant_id(db: Session):
    tid = uuid4()
    db.execute(
        text(
            "INSERT INTO tenants (id, name, slug, active, created_at) "
            "VALUES (:id, :name, :slug, :active, :created_at)"
        ),
        {
            "id": str(tid),
            "name": "Sprint2 HR",
            "slug": f"s2-hr-{tid.hex[:8]}",
            "active": True,
            "created_at": datetime.utcnow(),
        },
    )
    db.flush()
    return tid


def _configure_tenant_payroll(
    db: Session,
    tenant_id,
    *,
    country_code: str,
    currency: str = "EUR",
    payroll_settings: dict | None = None,
):
    db.execute(
        text(
            "UPDATE tenants SET country_code = :country_code, base_currency = :currency "
            "WHERE id = :id"
        ),
        {"id": str(tenant_id), "country_code": country_code, "currency": currency},
    )
    company_settings = (
        db.query(CompanySettings).filter(CompanySettings.tenant_id == tenant_id).first()
    )
    if company_settings is None:
        company_settings = CompanySettings(
            tenant_id=tenant_id,
            default_language=f"es-{country_code}",
            timezone="America/Guayaquil" if country_code == "EC" else "Europe/Madrid",
            currency=currency,
            primary_color="#2563eb",
            secondary_color="#1e293b",
            settings={"hr": {"payroll": payroll_settings or {}}},
        )
        db.add(company_settings)
    else:
        company_settings.default_language = f"es-{country_code}"
        company_settings.timezone = (
            "America/Guayaquil" if country_code == "EC" else "Europe/Madrid"
        )
        company_settings.currency = currency
        company_settings.settings = {"hr": {"payroll": payroll_settings or {}}}
    db.flush()


@pytest.fixture
def employee(db: Session, tenant_id):
    """Crea empleado de prueba."""
    emp = Employee(
        tenant_id=tenant_id,
        first_name="Juan",
        last_name="García",
        national_id="12345678Z",
        email="juan@example.com",
        phone="+34 600 000 000",
        birth_date=date(1990, 5, 15),
        contract_type="PERMANENT",
        status="ACTIVE",
        hire_date=date(2024, 1, 1),
        department="Operaciones",
        job_title="Gerente",
        country="ES",
    )
    db.add(emp)
    db.flush()
    return emp


@pytest.fixture
def employee_salary(db: Session, employee):
    """Crea configuración salarial."""
    salary = EmployeeSalary(
        employee_id=employee.id,
        salary_amount=Decimal("2500.00"),
        currency="EUR",
        effective_date=date(2026, 1, 1),
    )
    db.add(salary)
    db.flush()
    return salary


# ============================================================================
# TESTS: Employee
# ============================================================================


def test_employee_creation(db: Session, tenant_id):
    """Test: crea empleado correctamente."""
    emp = Employee(
        tenant_id=tenant_id,
        first_name="Ana",
        last_name="López",
        national_id="87654321A",
        email="ana@example.com",
        contract_type="PERMANENT",
        status="ACTIVE",
        hire_date=date(2025, 6, 1),
        country="ES",
    )
    db.add(emp)
    db.flush()

    assert emp.id is not None
    assert emp.national_id == "87654321A"
    assert emp.status == "ACTIVE"


def test_employee_status_transitions(db: Session, employee):
    """Test: transiciones de estado de empleado."""
    assert employee.status == "ACTIVE"

    # Cambiar a inactivo
    employee.status = "INACTIVE"
    db.flush()
    assert employee.status == "INACTIVE"

    # Cambiar a en licencia
    employee.status = "ON_LEAVE"
    db.flush()
    assert employee.status == "ON_LEAVE"

    # Cambiar a terminado
    employee.status = "TERMINATED"
    employee.termination_date = date.today()
    db.flush()
    assert employee.status == "TERMINATED"


def test_employee_salary_history(db: Session, employee):
    """Test: historial de cambios salariales."""
    # Salario inicial
    salary1 = EmployeeSalary(
        employee_id=employee.id,
        salary_amount=Decimal("2000.00"),
        effective_date=date(2024, 1, 1),
    )
    db.add(salary1)
    db.flush()

    # Aumento salarial
    salary2 = EmployeeSalary(
        employee_id=employee.id,
        salary_amount=Decimal("2500.00"),
        effective_date=date(2025, 1, 1),
        end_date=date(2024, 12, 31),
    )
    salary1.end_date = date(2024, 12, 31)
    db.add(salary2)
    db.flush()

    assert len(employee.salaries) >= 2
    assert employee.salaries[0].salary_amount == Decimal("2000.00")
    assert employee.salaries[1].salary_amount == Decimal("2500.00")


def test_employee_deductions(db: Session, employee):
    """Test: configurar deducciones del empleado."""
    # IRPF
    irpf = EmployeeDeduction(
        employee_id=employee.id,
        deduction_type="IRPF",
        percentage=Decimal("21.00"),
        effective_date=date(2026, 1, 1),
    )
    # Seguro
    mutual = EmployeeDeduction(
        employee_id=employee.id,
        deduction_type="MUTUAL",
        percentage=Decimal("1.25"),
        effective_date=date(2026, 1, 1),
    )
    db.add(irpf)
    db.add(mutual)
    db.flush()

    assert len(employee.deductions) == 2
    assert employee.deductions[0].deduction_type == "IRPF"


# ============================================================================
# TESTS: Payroll Calculations
# ============================================================================


def test_irpf_calculation_bracket_1(db: Session):
    """Test: calcula IRPF en primer tramo (19%)."""
    gross = Decimal("10000.00")
    irpf = PayrollService.calculate_irpf(gross, "ES", 2026)

    # 19% de 10.000 = 1.900
    assert irpf == Decimal("1900.00")


def test_irpf_calculation_bracket_2(db: Session):
    """Test: calcula IRPF en segundo tramo (progresivo)."""
    gross = Decimal("25000.00")
    irpf = PayrollService.calculate_irpf(gross, "ES", 2026)

    # Primer tramo: 12.450 * 19% = 2.365,50
    # Segundo tramo: (25.000 - 12.450) * 21% = 2.635,50
    # Total: 5.001
    expected = (Decimal("12450.00") * Decimal("0.19")) + (
        (Decimal("25000.00") - Decimal("12450.00")) * Decimal("0.21")
    )
    assert irpf == expected


def test_social_security_employee(db: Session):
    """Test: calcula aportación Seguridad Social empleado."""
    gross = Decimal("2500.00")
    ss = PayrollService.calculate_social_security(gross, "ES", 2026, employee=True)

    # 6.35% de 2.500 = 158,75
    expected = Decimal("2500.00") * Decimal("6.35") / 100
    assert ss == expected


def test_social_security_employer(db: Session):
    """Test: calcula aportación Seguridad Social empleador."""
    gross = Decimal("2500.00")
    ss = PayrollService.calculate_social_security(gross, "ES", 2026, employee=False)

    # 23.60% de 2.500 = 590,00
    expected = Decimal("2500.00") * Decimal("23.60") / 100
    assert ss == expected


# ============================================================================
# TESTS: Payroll Generation
# ============================================================================


def test_payroll_generation_single_employee(db: Session, tenant_id, employee, employee_salary):
    """Test: genera nómina con un empleado."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.payroll_month == "2026-02"
    assert payroll.status == "DRAFT"
    assert payroll.total_employees == 1
    assert payroll.total_gross == employee_salary.salary_amount
    assert payroll.total_net > Decimal("0")
    assert payroll.total_net < payroll.total_gross


def test_payroll_details_calculation(db: Session, tenant_id, employee, employee_salary):
    """Test: detalle de nómina calcula correctamente."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    detail = (
        db.query(PayrollDetail).filter_by(payroll_id=payroll.id, employee_id=employee.id).first()
    )

    assert detail is not None
    assert detail.gross_salary == Decimal("2500.00")
    assert detail.irpf > Decimal("0")
    assert detail.social_security > Decimal("0")
    assert detail.net_salary == (detail.gross_salary - detail.total_deductions)


def test_payroll_tax_summary(db: Session, tenant_id, employee, employee_salary):
    """Test: resumen de impuestos en nómina."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    taxes = db.query(PayrollTax).filter_by(payroll_id=payroll.id).all()

    # Debe haber registros de IRPF, SS empleado, SS empleador
    tax_types = [t.tax_type for t in taxes]
    assert "IRPF" in tax_types
    assert "SOCIAL_SECURITY_EMPLOYEE" in tax_types
    assert "SOCIAL_SECURITY_EMPLOYER" in tax_types


def test_payroll_multiple_employees(db: Session, tenant_id):
    """Test: genera nómina con múltiples empleados."""
    # Crear 3 empleados
    employees = []
    for i in range(3):
        emp = Employee(
            tenant_id=tenant_id,
            first_name=f"Empleado{i}",
            last_name="Test",
            national_id=f"1234567{i}Z",
            email=f"emp{i}@example.com",
            contract_type="PERMANENT",
            status="ACTIVE",
            hire_date=date(2024, 1, 1),
            country="ES",
        )
        db.add(emp)
        db.flush()

        salary = EmployeeSalary(
            employee_id=emp.id,
            salary_amount=Decimal("2000.00") + (i * Decimal("500.00")),
            effective_date=date(2026, 1, 1),
        )
        db.add(salary)
        db.flush()
        employees.append(emp)

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.total_employees == 3

    details = db.query(PayrollDetail).filter_by(payroll_id=payroll.id).all()
    assert len(details) == 3


def test_payroll_daily_rate_uses_distinct_work_days(db: Session, tenant_id, employee, employee_salary):
    employee_salary.salary_amount = Decimal("50.00")
    employee_salary.notes = build_salary_notes("diario")
    db.add_all(
        [
            TimeEntry(
                tenant_id=str(tenant_id),
                employee_id=employee.id,
                entry_date=date(2026, 2, 7),
                clock_in_time=datetime.strptime("08:00", "%H:%M").time(),
                clock_out_time=datetime.strptime("12:00", "%H:%M").time(),
                entry_type="trabajo",
            ),
            TimeEntry(
                tenant_id=str(tenant_id),
                employee_id=employee.id,
                entry_date=date(2026, 2, 7),
                clock_in_time=datetime.strptime("13:00", "%H:%M").time(),
                clock_out_time=datetime.strptime("15:00", "%H:%M").time(),
                entry_type="trabajo",
            ),
            TimeEntry(
                tenant_id=str(tenant_id),
                employee_id=employee.id,
                entry_date=date(2026, 2, 14),
                clock_in_time=datetime.strptime("08:00", "%H:%M").time(),
                clock_out_time=datetime.strptime("12:00", "%H:%M").time(),
                entry_type="trabajo",
            ),
        ]
    )
    db.flush()

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.total_gross == Decimal("100.00")


def test_payroll_daily_rate_falls_back_to_business_days_without_entries(
    db: Session, tenant_id, employee, employee_salary
):
    _configure_tenant_payroll(db, tenant_id, country_code="ES", currency="EUR")
    employee.hire_date = date(2026, 2, 11)
    employee_salary.salary_amount = Decimal("50.00")
    employee_salary.notes = build_salary_notes("diario")
    db.flush()

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.total_gross == Decimal("650.00")


def test_payroll_uses_latest_salary_when_effective_date_is_the_same(
    db: Session, tenant_id, employee, employee_salary
):
    _configure_tenant_payroll(db, tenant_id, country_code="ES", currency="EUR")
    employee_salary.salary_amount = Decimal("0.00")
    employee_salary.notes = build_salary_notes("mensual")
    db.flush()

    latest_salary = EmployeeSalary(
        employee_id=employee.id,
        salary_amount=Decimal("20.00"),
        currency="EUR",
        effective_date=date(2026, 1, 1),
        notes=build_salary_notes("diario"),
        created_at=datetime.now(UTC),
    )
    db.add(latest_salary)
    db.flush()

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.total_gross == Decimal("400.00")


def test_payroll_hourly_rate_uses_worked_hours(db: Session, tenant_id, employee, employee_salary):
    _configure_tenant_payroll(db, tenant_id, country_code="ES", currency="EUR")
    employee_salary.salary_amount = Decimal("10.00")
    employee_salary.notes = build_salary_notes("por_hora")
    db.add_all(
        [
            TimeEntry(
                tenant_id=str(tenant_id),
                employee_id=employee.id,
                entry_date=date(2026, 2, 8),
                clock_in_time=datetime.strptime("08:00", "%H:%M").time(),
                clock_out_time=datetime.strptime("12:30", "%H:%M").time(),
                entry_type="trabajo",
            ),
            TimeEntry(
                tenant_id=str(tenant_id),
                employee_id=employee.id,
                entry_date=date(2026, 2, 15),
                clock_in_time=datetime.strptime("09:00", "%H:%M").time(),
                clock_out_time=datetime.strptime("13:00", "%H:%M").time(),
                entry_type="trabajo",
            ),
        ]
    )
    db.flush()

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.total_gross == Decimal("85.00")


def test_payroll_ec_daily_rate_without_entries_defaults_to_single_direct_day(
    db: Session, tenant_id, employee, employee_salary
):
    _configure_tenant_payroll(db, tenant_id, country_code="EC", currency="USD")
    employee.country = "ES"
    employee.hire_date = date(2026, 3, 11)
    employee_salary.salary_amount = Decimal("20.00")
    employee_salary.notes = build_salary_notes("diario")
    employee_salary.effective_date = date(2026, 3, 11)
    db.flush()

    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-03", date(2026, 3, 12))

    assert payroll.total_gross == Decimal("20.00")
    assert payroll.total_deductions == Decimal("0")
    assert payroll.total_net == Decimal("20.00")


# ============================================================================
# TESTS: Payroll States
# ============================================================================


def test_payroll_state_transitions(db: Session, tenant_id, employee, employee_salary):
    """Test: transiciones de estado de nómina."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    assert payroll.status == "DRAFT"

    # Confirmar
    user_id = uuid4()
    payroll = PayrollService.confirm_payroll(db, payroll.id, user_id)
    assert payroll.status == "CONFIRMED"
    assert payroll.confirmed_by == user_id

    # Marcar como pagada
    payroll = PayrollService.mark_payroll_paid(db, payroll.id)
    assert payroll.status == "PAID"


def test_confirm_payroll_creates_payroll_expense(db: Session, tenant_id, employee, employee_salary):
    """Test: confirmar nÃ³mina genera gasto operativo de payroll."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))
    user_id = uuid4()

    PayrollService.confirm_payroll(db, payroll.id, user_id)

    expense = (
        db.query(Expense)
        .filter_by(
            invoice_number=f"PAYROLL-{payroll.id}",
        )
        .first()
    )

    assert expense is not None
    assert expense.category == "payroll"
    assert expense.status == "pending"
    assert expense.concept == "Nomina 2026-02"
    assert Decimal(str(expense.amount)) == (
        payroll.total_gross + payroll.total_social_security_employer
    )


def test_mark_payroll_paid_updates_existing_payroll_expense(
    db: Session, tenant_id, employee, employee_salary
):
    """Test: pagar nÃ³mina actualiza el gasto existente sin duplicarlo."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))
    PayrollService.confirm_payroll(db, payroll.id, uuid4())

    PayrollService.mark_payroll_paid(db, payroll.id)

    expenses = (
        db.query(Expense)
        .filter_by(
            invoice_number=f"PAYROLL-{payroll.id}",
        )
        .all()
    )

    assert len(expenses) == 1
    assert expenses[0].status == "paid"
    assert Decimal(str(expenses[0].pending_amount or 0)) == Decimal("0")
    assert Decimal(str(expenses[0].paid_amount or 0)) == Decimal(str(expenses[0].amount))


def test_payroll_cannot_modify_after_confirm(db: Session, tenant_id, employee, employee_salary):
    """Test: no se puede modificar nómina después de confirmar."""
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    # Confirmar
    PayrollService.confirm_payroll(db, payroll.id, uuid4())

    # Intentar confirmar de nuevo debe fallar
    with pytest.raises(ValueError, match="Cannot confirm payroll"):
        PayrollService.confirm_payroll(db, payroll.id, uuid4())


def test_payroll_cannot_generate_duplicate_period(db: Session, tenant_id, employee, employee_salary):
    PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    with pytest.raises(ValueError, match="Payroll already exists"):
        PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))


def test_delete_payroll_allows_draft_only(db: Session, tenant_id, employee, employee_salary):
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))
    payroll_id = payroll.id

    PayrollService.delete_payroll(db, payroll_id)
    db.flush()

    assert db.get(type(payroll), payroll_id) is None


# ============================================================================
# TESTS: Payment Slips
# ============================================================================


def test_payslip_generation(db: Session, tenant_id, employee, employee_salary):
    """Test: genera boletas de pago."""
    PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    payslips = db.query(PaymentSlip).filter_by(tenant_id=str(tenant_id)).all()

    assert len(payslips) >= 1
    assert payslips[0].status == "GENERATED"
    assert payslips[0].valid_until == date(2026, 3, 1)
    assert payslips[0].download_count == 0


def test_payslip_access_tracking(db: Session, tenant_id, employee, employee_salary):
    """Test: registra acceso a boletas."""
    PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))

    payslip = db.query(PaymentSlip).filter_by(tenant_id=str(tenant_id)).first()

    # Simular descargas
    payslip.download_count += 1
    payslip.viewed_at = date.today()
    db.flush()

    assert payslip.download_count == 1
    assert payslip.viewed_at is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_full_payroll_workflow(db: Session, tenant_id, employee, employee_salary):
    """Test: flujo completo de nómina."""
    # Generar
    payroll = PayrollService.generate_payroll(db, tenant_id, "2026-02", date(2026, 2, 28))
    assert payroll.status == "DRAFT"

    # Confirmar
    user_id = uuid4()
    payroll = PayrollService.confirm_payroll(db, payroll.id, user_id)
    assert payroll.status == "CONFIRMED"
    assert payroll.confirmed_at is not None

    # Marcar pagada
    payroll = PayrollService.mark_payroll_paid(db, payroll.id)
    assert payroll.status == "PAID"

    # Verificar boleta
    payslip = db.query(PaymentSlip).filter_by(tenant_id=str(tenant_id)).first()
    assert payslip.status == "GENERATED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
