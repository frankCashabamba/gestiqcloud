"""HR Service - Payroll Generation and Management"""

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select, text
from sqlalchemy.orm import Session

from app.models.company.company_settings import CompanySettings
from app.models.expenses.expense import Expense
from app.models.hr.attendance import TimeEntry
from app.models.hr.employee import Employee, EmployeeSalary
from app.models.hr.payroll import Payroll, PayrollDetail, PayrollTax
from app.models.hr.payslip import PaymentSlip
from app.models.tenant import Tenant
from app.modules.hr.application.compensation import (
    month_bounds,
    normalize_payment_mode,
    parse_salary_notes,
    time_entry_hours,
)

logger = logging.getLogger(__name__)

PAYROLL_EXPENSE_PREFIX = "PAYROLL-"


class PayrollService:
    """Servicio para generar y gestionar nóminas."""

    @staticmethod
    def _db_uuid(db: Session, value: UUID | None) -> UUID | str | None:
        if value is None:
            return None
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            return str(value)
        return value

    @staticmethod
    def _db_tenant_id(db: Session, value: UUID | str | None) -> UUID | str | None:
        if value is None:
            return None
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            return str(value)
        return value

    @staticmethod
    def _country_from_locale(locale: str | None) -> str | None:
        if not locale:
            return None
        normalized = str(locale).strip().replace("_", "-")
        if "-" not in normalized:
            return None
        country_code = normalized.rsplit("-", 1)[-1].strip().upper()
        return country_code if len(country_code) == 2 else None

    @staticmethod
    def _parse_decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_bool(value: Any, default: bool) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "si", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return default

    @staticmethod
    def _default_payroll_parameters(country: str, year: int) -> dict[str, Any]:
        country = (country or "ES").upper()
        if country == "ES" and year == 2026:
            return {
                "smi": Decimal("1464.00"),
                "ss_employee_rate": Decimal("6.35"),
                "ss_employer_rate": Decimal("23.60"),
                "mutual_insurance_rate": Decimal("1.25"),
                "irpf_brackets": [
                    {"min": 0, "max": 12450, "rate": Decimal("19.00")},
                    {"min": 12450, "max": 35200, "rate": Decimal("21.00")},
                    {"min": 35200, "max": 60000, "rate": Decimal("28.00")},
                    {"min": 60000, "max": 300000, "rate": Decimal("37.00")},
                    {"min": 300000, "max": float("inf"), "rate": Decimal("45.00")},
                ],
            }
        if country == "EC" and year == 2026:
            return {
                "smi": Decimal("460.00"),
                "ss_employee_rate": Decimal("9.45"),
                "ss_employer_rate": Decimal("11.15"),
                "mutual_insurance_rate": Decimal("0.00"),
                "irpf_brackets": [],
            }
        raise ValueError(f"Parameters not found for {country}/{year}")

    @staticmethod
    def _ensure_payroll_parameters_table(db: Session) -> None:
        db.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS payroll_parameters (
                    tenant_id TEXT NULL,
                    country VARCHAR(2) NOT NULL,
                    year INTEGER NOT NULL,
                    smi NUMERIC(14,2) NULL,
                    ss_employee_rate NUMERIC(8,4) NULL,
                    ss_employer_rate NUMERIC(8,4) NULL,
                    mutual_insurance_rate NUMERIC(8,4) NULL,
                    irpf_brackets_json TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        try:
            db.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_payroll_parameters_scope "
                    "ON payroll_parameters (tenant_id, country, year)"
                )
            )
        except Exception:
            pass

    @staticmethod
    def _load_payroll_parameters_from_db(
        db: Session,
        tenant_id: UUID,
        country: str,
        year: int,
    ) -> dict[str, Any] | None:
        PayrollService._ensure_payroll_parameters_table(db)
        tenant_key = str(tenant_id)
        row = (
            db.execute(
                text(
                    """
                SELECT tenant_id, smi, ss_employee_rate, ss_employer_rate,
                       mutual_insurance_rate, irpf_brackets_json
                FROM payroll_parameters
                WHERE country = :country
                  AND year = :year
                  AND (tenant_id = :tenant_id OR tenant_id IS NULL)
                ORDER BY CASE WHEN tenant_id = :tenant_id THEN 0 ELSE 1 END
                LIMIT 1
                """
                ),
                {"tenant_id": tenant_key, "country": country, "year": year},
            )
            .mappings()
            .first()
        )
        if not row:
            return None

        try:
            brackets_raw = json.loads(row["irpf_brackets_json"] or "[]")
        except Exception:
            brackets_raw = []
        brackets: list[dict[str, Any]] = []
        for item in brackets_raw:
            if not isinstance(item, dict):
                continue
            brackets.append(
                {
                    "min": float(item.get("min", 0) or 0),
                    "max": float(item.get("max", float("inf")) or float("inf")),
                    "rate": PayrollService._parse_decimal(item.get("rate")) or Decimal("0"),
                }
            )

        return {
            "smi": PayrollService._parse_decimal(row["smi"]) or Decimal("0"),
            "ss_employee_rate": PayrollService._parse_decimal(row["ss_employee_rate"]),
            "ss_employer_rate": PayrollService._parse_decimal(row["ss_employer_rate"]),
            "mutual_insurance_rate": PayrollService._parse_decimal(row["mutual_insurance_rate"]),
            "irpf_brackets": brackets,
        }

    @staticmethod
    def _default_payroll_rules(country_code: str) -> dict[str, Any]:
        country = (country_code or "ES").upper()
        if country == "ES":
            return {
                "apply_income_tax": True,
                "apply_social_security_employee": True,
                "apply_social_security_employer": True,
                "apply_mutual_insurance": True,
                "income_tax_rate": None,
                "social_security_employee_rate": Decimal("6.35"),
                "social_security_employer_rate": Decimal("23.60"),
                "mutual_insurance_rate": Decimal("1.25"),
                "daily_without_entries_strategy": "business_days",
            }
        if country == "EC":
            return {
                "apply_income_tax": False,
                "apply_social_security_employee": False,
                "apply_social_security_employer": False,
                "apply_mutual_insurance": False,
                "income_tax_rate": None,
                "social_security_employee_rate": None,
                "social_security_employer_rate": None,
                "mutual_insurance_rate": None,
                "daily_without_entries_strategy": "single_day",
            }
        return {
            "apply_income_tax": False,
            "apply_social_security_employee": False,
            "apply_social_security_employer": False,
            "apply_mutual_insurance": False,
            "income_tax_rate": None,
            "social_security_employee_rate": None,
            "social_security_employer_rate": None,
            "mutual_insurance_rate": None,
            "daily_without_entries_strategy": "none",
        }

    @staticmethod
    def _tenant_payroll_context(db: Session, tenant_id: UUID) -> dict[str, Any]:
        tenant_key = PayrollService._db_tenant_id(db, tenant_id)
        tenant = db.execute(select(Tenant).where(Tenant.id == tenant_key)).scalars().first()
        company_settings = (
            db.execute(select(CompanySettings).where(CompanySettings.tenant_id == tenant_key))
            .scalars()
            .first()
        )
        settings_json = (
            company_settings.settings
            if company_settings and isinstance(company_settings.settings, dict)
            else {}
        )
        hr_settings = settings_json.get("hr") if isinstance(settings_json.get("hr"), dict) else {}
        payroll_settings = (
            hr_settings.get("payroll") if isinstance(hr_settings.get("payroll"), dict) else {}
        )
        locale = company_settings.default_language if company_settings else None
        country_code = (
            getattr(tenant, "country_code", None)
            or settings_json.get("pais")
            or PayrollService._country_from_locale(locale)
            or getattr(tenant, "country", None)
            or "ES"
        )
        currency = (
            (company_settings.currency if company_settings else None)
            or getattr(tenant, "base_currency", None)
            or ""
        )
        return {
            "country_code": str(country_code).strip().upper(),
            "currency": str(currency).strip().upper(),
            "payroll_settings": payroll_settings,
        }

    @staticmethod
    def _payroll_rules(
        country_code: str,
        payroll_settings: dict[str, Any] | None,
        payroll_parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rules = PayrollService._default_payroll_rules(country_code)
        parameters = payroll_parameters if isinstance(payroll_parameters, dict) else {}
        if parameters:
            if parameters.get("ss_employee_rate") is not None:
                rules["social_security_employee_rate"] = PayrollService._parse_decimal(
                    parameters.get("ss_employee_rate")
                )
            if parameters.get("ss_employer_rate") is not None:
                rules["social_security_employer_rate"] = PayrollService._parse_decimal(
                    parameters.get("ss_employer_rate")
                )
            if parameters.get("mutual_insurance_rate") is not None:
                rules["mutual_insurance_rate"] = PayrollService._parse_decimal(
                    parameters.get("mutual_insurance_rate")
                )
            if parameters.get("irpf_brackets"):
                rules["apply_income_tax"] = True
                rules["income_tax_rate"] = None
        settings = payroll_settings if isinstance(payroll_settings, dict) else {}
        if not settings:
            return rules

        if "deductions_enabled" in settings and not PayrollService._parse_bool(
            settings.get("deductions_enabled"), True
        ):
            rules["apply_income_tax"] = False
            rules["apply_social_security_employee"] = False
            rules["apply_social_security_employer"] = False
            rules["apply_mutual_insurance"] = False

        if "apply_income_tax" in settings:
            rules["apply_income_tax"] = PayrollService._parse_bool(
                settings.get("apply_income_tax"), rules["apply_income_tax"]
            )
        if "apply_social_security_employee" in settings:
            rules["apply_social_security_employee"] = PayrollService._parse_bool(
                settings.get("apply_social_security_employee"),
                rules["apply_social_security_employee"],
            )
        if "apply_social_security_employer" in settings:
            rules["apply_social_security_employer"] = PayrollService._parse_bool(
                settings.get("apply_social_security_employer"),
                rules["apply_social_security_employer"],
            )
        if "apply_mutual_insurance" in settings:
            rules["apply_mutual_insurance"] = PayrollService._parse_bool(
                settings.get("apply_mutual_insurance"), rules["apply_mutual_insurance"]
            )

        for key in (
            "income_tax_rate",
            "social_security_employee_rate",
            "social_security_employer_rate",
            "mutual_insurance_rate",
        ):
            if key in settings:
                rules[key] = PayrollService._parse_decimal(settings.get(key))

        strategy = (
            str(
                settings.get("daily_without_entries_strategy")
                or rules["daily_without_entries_strategy"]
            )
            .strip()
            .lower()
        )
        if strategy not in {"business_days", "single_day", "none"}:
            strategy = rules["daily_without_entries_strategy"]
        rules["daily_without_entries_strategy"] = strategy
        return rules

    @staticmethod
    def _percentage_amount(gross: Decimal, rate: Decimal | None) -> Decimal:
        if rate is None:
            return Decimal("0")
        return (gross * rate) / 100

    @staticmethod
    def _income_tax_amount(
        gross: Decimal,
        *,
        country_code: str,
        year: int,
        payroll_rules: dict[str, Any],
    ) -> Decimal:
        if not payroll_rules.get("apply_income_tax", False):
            return Decimal("0")
        rate = payroll_rules.get("income_tax_rate")
        if rate is not None:
            return PayrollService._percentage_amount(gross, rate)
        if country_code == "ES":
            return PayrollService.calculate_irpf(gross, country_code, year)
        return Decimal("0")

    @staticmethod
    def _social_security_amount(
        gross: Decimal,
        *,
        country_code: str,
        year: int,
        employee: bool,
        payroll_rules: dict[str, Any],
    ) -> Decimal:
        apply_key = (
            "apply_social_security_employee" if employee else "apply_social_security_employer"
        )
        rate_key = "social_security_employee_rate" if employee else "social_security_employer_rate"
        if not payroll_rules.get(apply_key, False):
            return Decimal("0")
        rate = payroll_rules.get(rate_key)
        if rate is not None:
            return PayrollService._percentage_amount(gross, rate)
        if country_code == "ES":
            return PayrollService.calculate_social_security(
                gross, country_code, year, employee=employee
            )
        return Decimal("0")

    @staticmethod
    def _mutual_insurance_amount(
        gross: Decimal,
        *,
        country_code: str,
        year: int,
        payroll_rules: dict[str, Any],
    ) -> Decimal:
        if not payroll_rules.get("apply_mutual_insurance", False):
            return Decimal("0")
        rate = payroll_rules.get("mutual_insurance_rate")
        if rate is not None:
            return PayrollService._percentage_amount(gross, rate)
        if country_code == "ES":
            return PayrollService._percentage_amount(gross, Decimal("1.25"))
        return Decimal("0")

    @staticmethod
    def _payroll_expense_ref(payroll_id: UUID) -> str:
        return f"{PAYROLL_EXPENSE_PREFIX}{payroll_id}"

    @staticmethod
    def _payroll_expense_amount(payroll: Payroll) -> Decimal:
        gross = Decimal(str(payroll.total_gross or 0))
        employer_ss = Decimal(str(payroll.total_social_security_employer or 0))
        return gross + employer_ss

    @staticmethod
    def _refresh_profit_snapshot(db: Session, payroll: Payroll) -> None:
        """Refresh the real-profit snapshot for the payroll posting date."""
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            return
        try:
            from app.modules.reports.application.recalculation_service import RecalculationService

            RecalculationService(db).recalculate_daily(payroll.tenant_id, payroll.payroll_date)
        except Exception as exc:
            logger.warning(
                "Failed to refresh profit snapshot for payroll %s on %s: %s",
                payroll.id,
                payroll.payroll_date,
                exc,
            )

    @staticmethod
    def _sync_payroll_expense(
        db: Session,
        payroll: Payroll,
        *,
        user_id: UUID | None = None,
        mark_paid: bool = False,
    ) -> Expense:
        """Create or update the expense row that represents payroll cost."""
        owner_id = user_id or payroll.confirmed_by or payroll.created_by
        if owner_id is None:
            raise ValueError("Cannot create payroll expense without user reference")

        amount = PayrollService._payroll_expense_amount(payroll)
        expense_ref = PayrollService._payroll_expense_ref(payroll.id)
        tenant_id = PayrollService._db_tenant_id(db, payroll.tenant_id)
        owner_id_db = PayrollService._db_uuid(db, owner_id)
        concept = f"Nomina {payroll.payroll_month}"
        status = "paid" if mark_paid else "pending"
        paid_amount = amount if mark_paid else Decimal("0")
        pending_amount = Decimal("0") if mark_paid else amount
        notes = (
            f"Generado automaticamente desde la nomina {payroll.payroll_month} " f"({payroll.id})"
        )

        expense = (
            db.execute(
                select(Expense).where(
                    Expense.tenant_id == tenant_id,
                    Expense.invoice_number == expense_ref,
                )
            )
            .scalars()
            .first()
        )

        if expense is None:
            expense = Expense(
                tenant_id=tenant_id,
                date=payroll.payroll_date,
                concept=concept,
                category="payroll",
                subcategory=payroll.payroll_month,
                amount=amount,
                vat=Decimal("0"),
                total=amount,
                payment_method="transfer",
                invoice_number=expense_ref,
                status=status,
                paid_amount=paid_amount,
                pending_amount=pending_amount,
                user_id=owner_id_db,
                notes=notes,
            )
            db.add(expense)
        else:
            expense.date = payroll.payroll_date
            expense.concept = concept
            expense.category = "payroll"
            expense.subcategory = payroll.payroll_month
            expense.amount = amount
            expense.vat = Decimal("0")
            expense.total = amount
            expense.payment_method = expense.payment_method or "transfer"
            expense.status = status
            expense.paid_amount = paid_amount
            expense.pending_amount = pending_amount
            expense.notes = notes
            if not expense.user_id:
                expense.user_id = owner_id_db

        db.flush()
        PayrollService._post_payroll_journal(db, expense, payroll.tenant_id, owner_id)
        PayrollService._refresh_profit_snapshot(db, payroll)
        return expense

    @staticmethod
    def _post_payroll_journal(
        db: Session,
        expense: "Expense",
        tenant_id,
        user_id,
    ) -> None:
        """Genera/actualiza el asiento contable para el gasto de nómina."""
        try:
            from app.modules.expenses.application.journal import ExpenseJournalService

            tid = PayrollService._db_uuid(db, tenant_id)
            uid = PayrollService._db_uuid(db, user_id) if user_id else None
            svc = ExpenseJournalService(db, tid, uid)
            # on_update revierte el asiento previo si ya existía y crea uno nuevo
            svc.on_update(expense)
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Could not post journal entry for payroll expense %s", expense.id
            )

    @staticmethod
    def get_payroll_parameters(db: Session, tenant_id: UUID, country: str, year: int) -> dict:
        """Obtiene parametros de nomina desde BD con fallback a defaults."""
        normalized_country = str(country or "ES").strip().upper()
        from_db = PayrollService._load_payroll_parameters_from_db(
            db, tenant_id, normalized_country, year
        )
        if from_db:
            defaults = PayrollService._default_payroll_parameters(normalized_country, year)
            merged = {**defaults, **{k: v for k, v in from_db.items() if v is not None}}
            if from_db.get("irpf_brackets"):
                merged["irpf_brackets"] = from_db["irpf_brackets"]
            return merged
        return PayrollService._default_payroll_parameters(normalized_country, year)

    @staticmethod
    def calculate_irpf(gross: Decimal, country: str, year: int, db: Session = None) -> Decimal:
        """Calcula impuesto sobre la renta segun brackets configurados."""
        normalized_country = str(country or "ES").strip().upper()
        params = None
        if db is not None:
            params = PayrollService._load_payroll_parameters_from_db(
                db,
                UUID(int=0),
                normalized_country,
                year,
            )
        if not params:
            params = PayrollService._default_payroll_parameters(normalized_country, year)

        brackets = params.get("irpf_brackets") or []
        gross_amount = Decimal(str(gross or 0))
        if gross_amount <= 0 or not brackets:
            return Decimal("0.00")

        tax = Decimal("0")
        previous_limit = Decimal("0")
        for bracket in brackets:
            limit = Decimal(str(bracket.get("max", gross_amount)))
            rate = PayrollService._parse_decimal(bracket.get("rate")) or Decimal("0")
            if gross_amount <= previous_limit:
                break
            taxable = min(gross_amount, limit) - previous_limit
            tax += taxable * (rate / Decimal("100"))
            previous_limit = limit

        return tax.quantize(Decimal("0.01"))

    @staticmethod
    def calculate_social_security(
        gross: Decimal,
        country: str,
        year: int,
        employee: bool = True,
        db: Session | None = None,
    ) -> Decimal:
        """Calcula aportacion de Seguridad Social."""
        normalized_country = str(country or "ES").strip().upper()
        params = None
        if db is not None:
            params = PayrollService._load_payroll_parameters_from_db(
                db,
                UUID(int=0),
                normalized_country,
                year,
            )
        if not params:
            params = PayrollService._default_payroll_parameters(normalized_country, year)

        rate_key = "ss_employee_rate" if employee else "ss_employer_rate"
        rate = PayrollService._parse_decimal(params.get(rate_key)) or Decimal("0")
        return ((Decimal(str(gross or 0)) * rate) / Decimal("100")).quantize(Decimal("0.01"))

    @staticmethod
    def _existing_payroll_for_month(
        db: Session, tenant_id: UUID, payroll_month: str
    ) -> Payroll | None:
        return (
            db.execute(
                select(Payroll)
                .where(
                    Payroll.tenant_id == PayrollService._db_tenant_id(db, tenant_id),
                    Payroll.payroll_month == payroll_month,
                )
                .order_by(Payroll.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )

    @staticmethod
    def _count_business_days(start: date, end: date) -> int:
        if end < start:
            return 0
        total = 0
        current = start
        while current <= end:
            if current.weekday() < 5:
                total += 1
            current = date.fromordinal(current.toordinal() + 1)
        return total

    @staticmethod
    def _daily_fallback_range(
        employee: Employee, month_start: date, month_end: date
    ) -> tuple[date, date] | None:
        start = max(employee.hire_date or month_start, month_start)
        end = month_end
        if employee.termination_date:
            end = min(end, employee.termination_date)
        if end < start:
            return None
        return start, end

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
        existing_payroll = PayrollService._existing_payroll_for_month(db, tenant_id, payroll_month)
        if existing_payroll is not None:
            raise ValueError(
                f"Payroll already exists for {payroll_month} with status {existing_payroll.status}"
            )

        # 1. Obtener empleados activos
        employees = (
            db.execute(
                select(Employee).where(
                    Employee.tenant_id == PayrollService._db_tenant_id(db, tenant_id),
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
            tenant_id=PayrollService._db_tenant_id(db, tenant_id),
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
        tenant_context = PayrollService._tenant_payroll_context(db, tenant_id)
        payroll_parameters = PayrollService.get_payroll_parameters(
            db, tenant_id, tenant_context["country_code"], year
        )
        payroll_rules = PayrollService._payroll_rules(
            tenant_context["country_code"],
            tenant_context.get("payroll_settings"),
            payroll_parameters,
        )

        for employee in employees:
            detail = PayrollService._calculate_employee_payroll(
                db,
                employee,
                payroll_month,
                year,
                payroll_date=payroll_date,
                country_code=tenant_context["country_code"],
                payroll_rules=payroll_rules,
            )
            detail.payroll_id = payroll.id

            total_gross += detail.gross_salary
            total_irpf += detail.irpf
            total_ss_employee += detail.social_security
            total_deductions += detail.total_deductions

            db.add(detail)
            db.flush()

            # Crear PaymentSlip
            payslip = PaymentSlip(
                tenant_id=PayrollService._db_tenant_id(db, tenant_id),
                payroll_detail_id=detail.id,
                employee_id=employee.id,
                access_token=f"slip_{detail.id}_{datetime.now(UTC).timestamp()}",
                valid_until=date(
                    year if payroll_month.endswith("12") else year,
                    int(payroll_month[5:]) + 1 if not payroll_month.endswith("12") else 1,
                    1,
                ),
                status="GENERATED",
            )
            db.add(payslip)

        # Calcular SS empleador
        total_ss_employer = PayrollService._social_security_amount(
            total_gross,
            country_code=tenant_context["country_code"],
            year=year,
            employee=False,
            payroll_rules=payroll_rules,
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
        *,
        payroll_date: date,
        country_code: str,
        payroll_rules: dict[str, Any],
    ) -> PayrollDetail:
        """Calcula salario neto para un empleado."""

        # Obtener salary vigente
        month_start, month_end = month_bounds(payroll_month)
        period_end = min(month_end, payroll_date)
        salary_rec = db.execute(
            select(EmployeeSalary)
            .where(
                EmployeeSalary.employee_id == employee.id,
                EmployeeSalary.effective_date <= period_end,
            )
            .order_by(
                EmployeeSalary.effective_date.desc(),
                desc(EmployeeSalary.created_at),
                desc(EmployeeSalary.id),
            )
            .limit(1)
        ).scalar_one_or_none()

        if not salary_rec:
            raise ValueError(f"No salary found for employee {employee.id}")

        salary_amount = Decimal(str(salary_rec.salary_amount or 0))
        payment_mode = normalize_payment_mode(
            parse_salary_notes(salary_rec.notes).get("payment_mode")
        )
        gross = PayrollService._calculate_gross_salary(
            db,
            employee=employee,
            payroll_month=payroll_month,
            payment_mode=payment_mode,
            rate_amount=salary_amount,
            month_start=month_start,
            month_end=period_end,
            payroll_rules=payroll_rules,
        )

        # Calcular deducciones
        irpf = PayrollService._income_tax_amount(
            gross,
            country_code=country_code,
            year=year,
            payroll_rules=payroll_rules,
        )
        ss_employee = PayrollService._social_security_amount(
            gross,
            country_code=country_code,
            year=year,
            employee=True,
            payroll_rules=payroll_rules,
        )
        mutual = PayrollService._mutual_insurance_amount(
            gross,
            country_code=country_code,
            year=year,
            payroll_rules=payroll_rules,
        )

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
            notes=PayrollService._payroll_detail_notes(
                db,
                employee=employee,
                payment_mode=payment_mode,
                rate_amount=salary_amount,
                month_start=month_start,
                month_end=period_end,
                payroll_rules=payroll_rules,
            ),
        )

        return detail

    @staticmethod
    def _work_entries(
        db: Session,
        *,
        employee_id: UUID,
        month_start: date,
        month_end: date,
    ) -> list[TimeEntry]:
        return (
            db.execute(
                select(TimeEntry).where(
                    TimeEntry.employee_id == employee_id,
                    TimeEntry.entry_type == "trabajo",
                    TimeEntry.entry_date >= month_start,
                    TimeEntry.entry_date <= month_end,
                )
            )
            .scalars()
            .all()
        )

    @staticmethod
    def _calculate_gross_salary(
        db: Session,
        *,
        employee: Employee,
        payroll_month: str,
        payment_mode: str,
        rate_amount: Decimal,
        month_start: date,
        month_end: date,
        payroll_rules: dict[str, Any],
    ) -> Decimal:
        if payment_mode == "monthly":
            return rate_amount

        entries = PayrollService._work_entries(
            db,
            employee_id=employee.id,
            month_start=month_start,
            month_end=month_end,
        )
        if payment_mode == "daily":
            days_worked = len({entry.entry_date for entry in entries})
            if days_worked == 0:
                strategy = payroll_rules.get("daily_without_entries_strategy", "none")
                fallback_range = PayrollService._daily_fallback_range(
                    employee, month_start, month_end
                )
                if fallback_range is None:
                    return Decimal("0")
                if strategy == "business_days":
                    days_worked = PayrollService._count_business_days(*fallback_range)
                elif strategy == "single_day":
                    days_worked = 1
                else:
                    return Decimal("0")
            return rate_amount * Decimal(days_worked)
        if payment_mode == "hourly":
            hours_worked = sum((time_entry_hours(entry) for entry in entries), Decimal("0"))
            return rate_amount * hours_worked
        raise ValueError(f"Unsupported payment mode {payment_mode} for employee {employee.id}")

    @staticmethod
    def _payroll_detail_notes(
        db: Session,
        *,
        employee: Employee,
        payment_mode: str,
        rate_amount: Decimal,
        month_start: date,
        month_end: date,
        payroll_rules: dict[str, Any],
    ) -> str | None:
        if payment_mode == "monthly":
            return "Modalidad mensual"
        entries = PayrollService._work_entries(
            db,
            employee_id=employee.id,
            month_start=month_start,
            month_end=month_end,
        )
        if payment_mode == "daily":
            days_worked = len({entry.entry_date for entry in entries})
            if days_worked == 0:
                strategy = payroll_rules.get("daily_without_entries_strategy", "none")
                fallback_range = PayrollService._daily_fallback_range(
                    employee, month_start, month_end
                )
                if fallback_range is None:
                    return f"Modalidad diaria: 0 dias x {rate_amount}"
                if strategy == "business_days":
                    days_worked = PayrollService._count_business_days(*fallback_range)
                    return (
                        f"Modalidad diaria estimada: {days_worked} dias laborables x {rate_amount}"
                    )
                if strategy == "single_day":
                    return f"Modalidad diaria directa: 1 dia x {rate_amount}"
                return f"Modalidad diaria: 0 dias x {rate_amount}"
            return f"Modalidad diaria: {days_worked} dias x {rate_amount}"
        if payment_mode == "hourly":
            hours_worked = sum((time_entry_hours(entry) for entry in entries), Decimal("0"))
            return f"Modalidad por hora: {hours_worked.normalize()} h x {rate_amount}"
        return None

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
        payroll.confirmed_at = datetime.now(UTC)

        PayrollService._sync_payroll_expense(db, payroll, user_id=confirmed_by, mark_paid=False)
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

        PayrollService._sync_payroll_expense(db, payroll, mark_paid=True)
        db.flush()
        return payroll

    @staticmethod
    def delete_payroll(db: Session, payroll_id: UUID) -> None:
        payroll = db.get(Payroll, payroll_id)
        if not payroll:
            raise ValueError(f"Payroll {payroll_id} not found")
        if payroll.status != "DRAFT":
            raise ValueError(f"Cannot delete payroll in status {payroll.status}")
        detail_ids = [detail.id for detail in payroll.details]
        if detail_ids:
            slips = (
                db.execute(select(PaymentSlip).where(PaymentSlip.payroll_detail_id.in_(detail_ids)))
                .scalars()
                .all()
            )
            for slip in slips:
                db.delete(slip)
        db.delete(payroll)
        db.flush()
