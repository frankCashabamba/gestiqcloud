"""HR Service - Payroll Generation and Management"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hr.employee import Employee, EmployeeSalary
from app.models.hr.payroll import Payroll, PayrollDetail, PayrollTax
from app.models.hr.payslip import PaymentSlip


class PayrollService:
    """Servicio para generar y gestionar nóminas."""

    @staticmethod
    def get_payroll_parameters(db: Session, tenant_id: UUID, country: str, year: int) -> dict:
        """
        Obtiene parámetros de impuestos desde BD.

        Busca en tabla payroll_parameters (que debe existir como master data).
        De momento retorna defaults para España 2026.
        """
        # TODO: Implementar lectura desde tabla payroll_parameters
        if country == "ES" and year == 2026:
            return {
                "smi": Decimal("1464.00"),  # Salario mínimo interprofesional
                "ss_employee_rate": Decimal("6.35"),  # %
                "ss_employer_rate": Decimal("23.60"),  # %
                "mutual_insurance_rate": Decimal("1.25"),  # % (promedio)
                "irpf_brackets": [
                    {"min": 0, "max": 12450, "rate": Decimal("19.00")},
                    {"min": 12450, "max": 35200, "rate": Decimal("21.00")},
                    {"min": 35200, "max": 60000, "rate": Decimal("28.00")},
                    {"min": 60000, "max": 300000, "rate": Decimal("37.00")},
                    {"min": 300000, "max": float("inf"), "rate": Decimal("45.00")},
                ],
            }

        raise ValueError(f"Parameters not found for {country}/{year}")

    @staticmethod
    def calculate_irpf(gross: Decimal, country: str, year: int, db: Session = None) -> Decimal:
        """Calcula IRPF según brackets."""
        if country == "ES" and year == 2026:
            # Tarifa progresiva España 2026
            brackets = [
                (Decimal("12450"), Decimal("19")),
                (Decimal("35200"), Decimal("21")),
                (Decimal("60000"), Decimal("28")),
                (Decimal("300000"), Decimal("37")),
                (Decimal("999999999"), Decimal("45")),
            ]

            irpf = Decimal("0")
            prev_limit = Decimal("0")

            for limit, rate in brackets:
                if gross <= prev_limit:
                    break
                taxable = min(gross, limit) - prev_limit
                irpf += taxable * (rate / 100)
                prev_limit = limit

            return irpf

        raise ValueError(f"IRPF calculation not implemented for {country}/{year}")

    @staticmethod
    def calculate_social_security(
        gross: Decimal, country: str, year: int, employee: bool = True
    ) -> Decimal:
        """Calcula aportación Seguridad Social."""
        if country == "ES" and year == 2026:
            rate = Decimal("6.35") if employee else Decimal("23.60")
            return (gross * rate) / 100

        raise ValueError(f"SS calculation not implemented for {country}/{year}")

    @staticmethod
    def generate_payroll(
        db: Session,
        tenant_id: UUID,
        payroll_month: str,  # "2026-02"
        payroll_date: date,
    ) -> Payroll:
        """
        Genera nómina para todos los empleados activos del mes.

        Proceso:
        1. Obtener empleados activos
        2. Por cada empleado: calcular salario neto
        3. Crear Payroll header
        4. Crear PayrollDetail para cada empleado
        5. Actualizar totales
        """
        # 1. Obtener empleados activos
        employees = (
            db.execute(
                select(Employee).where(
                    Employee.tenant_id == tenant_id,
                    Employee.status == "ACTIVE",
                )
            )
            .scalars()
            .all()
        )

        if not employees:
            raise ValueError("No active employees found")

        # 2. Crear Payroll header
        payroll = Payroll(
            tenant_id=tenant_id,
            payroll_month=payroll_month,
            payroll_date=payroll_date,
            status="DRAFT",
            total_employees=len(employees),
        )
        db.add(payroll)
        db.flush()

        # 3. Procesar cada empleado
        total_gross = Decimal("0")
        total_irpf = Decimal("0")
        total_ss_employee = Decimal("0")
        total_ss_employer = Decimal("0")
        total_deductions = Decimal("0")

        year = int(payroll_month[:4])

        for employee in employees:
            detail = PayrollService._calculate_employee_payroll(db, employee, payroll_month, year)
            detail.payroll_id = payroll.id

            total_gross += detail.gross_salary
            total_irpf += detail.irpf
            total_ss_employee += detail.social_security
            total_deductions += detail.total_deductions

            db.add(detail)

            # Crear PaymentSlip
            payslip = PaymentSlip(
                tenant_id=tenant_id,
                payroll_detail_id=detail.id,
                employee_id=employee.id,
                access_token=f"slip_{detail.id}_{datetime.utcnow().timestamp()}",
                valid_until=date(
                    year if payroll_month.endswith("12") else year,
                    int(payroll_month[5:]) + 1 if not payroll_month.endswith("12") else 1,
                    1,
                ),
                status="GENERATED",
            )
            db.add(payslip)

        # Calcular SS empleador
        total_ss_employer = PayrollService.calculate_social_security(
            total_gross, employee.country, year, employee=False
        )

        # 4. Actualizar totales en Payroll
        payroll.total_gross = total_gross
        payroll.total_irpf = total_irpf
        payroll.total_social_security_employee = total_ss_employee
        payroll.total_social_security_employer = total_ss_employer
        payroll.total_deductions = total_deductions
        payroll.total_net = total_gross - total_deductions

        # Crear registros de impuestos
        tax_records = [
            PayrollTax(payroll_id=payroll.id, tax_type="IRPF", total_amount=total_irpf),
            PayrollTax(
                payroll_id=payroll.id,
                tax_type="SOCIAL_SECURITY_EMPLOYEE",
                total_amount=total_ss_employee,
            ),
            PayrollTax(
                payroll_id=payroll.id,
                tax_type="SOCIAL_SECURITY_EMPLOYER",
                total_amount=total_ss_employer,
            ),
        ]
        for tax in tax_records:
            db.add(tax)

        db.flush()
        return payroll

    @staticmethod
    def _calculate_employee_payroll(
        db: Session,
        employee: Employee,
        payroll_month: str,
        year: int,
    ) -> PayrollDetail:
        """Calcula salario neto para un empleado."""

        # Obtener salary vigente
        month_date = date(int(payroll_month[:4]), int(payroll_month[5:]), 1)
        salary_rec = db.execute(
            select(EmployeeSalary)
            .where(
                EmployeeSalary.employee_id == employee.id,
                EmployeeSalary.effective_date <= month_date,
            )
            .order_by(EmployeeSalary.effective_date.desc())
            .limit(1)
        ).scalar_one_or_none()

        if not salary_rec:
            raise ValueError(f"No salary found for employee {employee.id}")

        gross = salary_rec.salary_amount

        # Calcular deducciones
        irpf = PayrollService.calculate_irpf(gross, employee.country, year)
        ss_employee = PayrollService.calculate_social_security(
            gross, employee.country, year, employee=True
        )
        mutual = PayrollService.calculate_social_security(
            gross, employee.country, year, employee=True
        ) * Decimal("0.25")  # Promedio 1.25%

        total_deductions = irpf + ss_employee + mutual
        net = gross - total_deductions

        detail = PayrollDetail(
            employee_id=employee.id,
            gross_salary=gross,
            irpf=irpf,
            social_security=ss_employee,
            mutual_insurance=mutual,
            other_deductions=Decimal("0"),
            total_deductions=total_deductions,
            net_salary=net,
        )

        return detail

    @staticmethod
    def confirm_payroll(db: Session, payroll_id: UUID, confirmed_by: UUID) -> Payroll:
        """Confirma nómina (cambio de DRAFT a CONFIRMED)."""
        payroll = db.get(Payroll, payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")

        if payroll.status != "DRAFT":
            raise ValueError(f"Cannot confirm payroll in status {payroll.status}")

        payroll.status = "CONFIRMED"
        payroll.confirmed_by = confirmed_by
        payroll.confirmed_at = datetime.utcnow()

        db.flush()
        return payroll

    @staticmethod
    def mark_payroll_paid(db: Session, payroll_id: UUID) -> Payroll:
        """Marca nómina como pagada."""
        payroll = db.get(Payroll, payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")

        if payroll.status != "CONFIRMED":
            raise ValueError(f"Cannot mark as paid. Current status: {payroll.status}")

        payroll.status = "PAID"

        db.flush()
        return payroll
