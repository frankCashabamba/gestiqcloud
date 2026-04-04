from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company.company_role import CompanyRole
from app.models.company.company_settings import CompanySettings
from app.models.company.company_user import CompanyUser
from app.models.company.company_user_role import CompanyUserRole
from app.models.hr.employee import Employee, EmployeeSalary
from app.models.tenant import Tenant
from app.modules.hr.application.compensation import (
    build_salary_notes,
    current_salary_amount,
    parse_salary_notes,
)

AUTO_SYNC_MARKER = "[auto-sync company-user:"


class EmployeeSyncService:
    @staticmethod
    def _db_tenant_id(db: Session, value: UUID | str | None) -> UUID | str | None:
        if value is None:
            return None
        if db.bind is not None and db.bind.dialect.name == "sqlite":
            return str(value)
        return value

    @staticmethod
    def _marker(user_id: UUID) -> str:
        return f"{AUTO_SYNC_MARKER}{user_id}]"

    @staticmethod
    def _has_marker(notes: str | None, user_id: UUID) -> bool:
        return EmployeeSyncService._marker(user_id) in (notes or "")

    @staticmethod
    def _merge_notes(notes: str | None, user_id: UUID) -> str:
        marker = EmployeeSyncService._marker(user_id)
        clean_notes = (notes or "").strip()
        if marker in clean_notes:
            return clean_notes
        if not clean_notes:
            return marker
        return f"{clean_notes}\n{marker}"

    @staticmethod
    def _auto_employee_code(user: CompanyUser) -> str:
        return f"USR-{str(user.id).split('-', 1)[0].upper()}"

    @staticmethod
    def _auto_document_number(user: CompanyUser) -> str:
        return f"USR-{str(user.id)}"

    @staticmethod
    def _default_hire_date(user: CompanyUser) -> date:
        created_at = getattr(user, "created_at", None)
        if created_at is not None:
            return created_at.date()
        return date.today()

    @staticmethod
    def _default_job_title(db: Session, user: CompanyUser) -> str | None:
        role_name = (
            db.execute(
                select(CompanyRole.name)
                .join(CompanyUserRole, CompanyUserRole.role_id == CompanyRole.id)
                .where(
                    CompanyUserRole.user_id == user.id,
                    CompanyUserRole.tenant_id
                    == EmployeeSyncService._db_tenant_id(db, user.tenant_id),
                    CompanyUserRole.is_active.is_(True),
                )
                .order_by(CompanyRole.name.asc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        return role_name or None

    @staticmethod
    def _find_employee(db: Session, user: CompanyUser) -> Employee | None:
        tenant_id = EmployeeSyncService._db_tenant_id(db, user.tenant_id)
        employees = (
            db.execute(
                select(Employee).where(
                    Employee.tenant_id == tenant_id,
                    (Employee.email == user.email) | (Employee.notes.ilike(f"%{user.id}%")),
                )
            )
            .scalars()
            .all()
        )
        for employee in employees:
            if employee.email == user.email or EmployeeSyncService._has_marker(
                employee.notes, user.id
            ):
                return employee
        return None

    @staticmethod
    def has_employee_profile(db: Session, user: CompanyUser) -> bool:
        return EmployeeSyncService._find_employee(db, user) is not None

    @staticmethod
    def _resolve_tenant_currency(db: Session, tenant_id: UUID | str | None) -> str:
        if tenant_id is None:
            return ""
        db_tid = EmployeeSyncService._db_tenant_id(db, tenant_id)
        settings = (
            db.execute(select(CompanySettings).where(CompanySettings.tenant_id == db_tid))
            .scalars()
            .first()
        )
        if settings and settings.currency:
            return str(settings.currency).strip().upper()
        tenant = db.execute(select(Tenant).where(Tenant.id == db_tid)).scalars().first()
        if tenant and tenant.base_currency:
            return str(tenant.base_currency).strip().upper()
        return ""

    @staticmethod
    def _ensure_salary(db: Session, employee: Employee, effective_date: date, currency: str = "") -> None:
        if employee.salaries:
            return
        db.add(
            EmployeeSalary(
                employee_id=employee.id,
                salary_amount=Decimal("0"),
                currency=currency,
                effective_date=effective_date,
                notes=build_salary_notes("mensual", "Auto-created from company user"),
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def sync_company_user(
        db: Session,
        user: CompanyUser,
        *,
        hire_date_override: date | None = None,
        department: str | None = None,
        job_title: str | None = None,
        salary_base: Decimal | None = None,
        payment_mode: str | None = None,
    ) -> Employee | None:
        if user.is_company_admin:
            return None

        employee = EmployeeSyncService._find_employee(db, user)
        resolved_job_title = job_title or EmployeeSyncService._default_job_title(db, user)
        hire_date = hire_date_override or EmployeeSyncService._default_hire_date(user)

        if employee is None and not user.is_active:
            return None

        if employee is None:
            employee = Employee(
                tenant_id=EmployeeSyncService._db_tenant_id(db, user.tenant_id),
                employee_code=EmployeeSyncService._auto_employee_code(user),
                first_name=(user.first_name or "").strip() or user.username or "Usuario",
                last_name=(user.last_name or "").strip() or "-",
                national_id=EmployeeSyncService._auto_document_number(user),
                email=user.email,
                contract_type="PERMANENT",
                status="ACTIVE",
                hire_date=hire_date,
                department=department,
                job_title=resolved_job_title,
                country="ES",
                notes=EmployeeSyncService._merge_notes(None, user.id),
            )
            db.add(employee)
            db.flush()
        else:
            employee.first_name = (
                (user.first_name or "").strip() or employee.first_name or "Usuario"
            )
            employee.last_name = (user.last_name or "").strip() or employee.last_name or "-"
            employee.email = user.email
            employee.status = "ACTIVE" if user.is_active else "INACTIVE"
            employee.hire_date = hire_date_override or employee.hire_date or hire_date
            employee.country = employee.country or "ES"
            if department is not None:
                employee.department = department or None
            if not employee.employee_code:
                employee.employee_code = EmployeeSyncService._auto_employee_code(user)
            if not employee.national_id:
                employee.national_id = EmployeeSyncService._auto_document_number(user)
            if resolved_job_title is not None:
                employee.job_title = resolved_job_title or None
            employee.notes = EmployeeSyncService._merge_notes(employee.notes, user.id)

        if user.is_active:
            tenant_currency = EmployeeSyncService._resolve_tenant_currency(db, user.tenant_id)
            if salary_base is None:
                EmployeeSyncService._ensure_salary(db, employee, employee.hire_date or hire_date, tenant_currency)
            else:
                current_salary = current_salary_amount(employee)
                desired_salary = Decimal(str(salary_base))
                if current_salary != desired_salary:
                    db.add(
                        EmployeeSalary(
                            employee_id=employee.id,
                            salary_amount=desired_salary,
                            currency=tenant_currency,
                            effective_date=employee.hire_date or hire_date,
                            notes=build_salary_notes(
                                payment_mode or "mensual",
                                "Updated from company user form",
                            ),
                            created_at=datetime.now(UTC),
                        )
                    )
                elif employee.salaries:
                    salary_record = max(employee.salaries, key=lambda item: item.effective_date)
                    free_notes = parse_salary_notes(salary_record.notes).get("notes")
                    salary_record.notes = build_salary_notes(
                        payment_mode or "mensual",
                        free_notes,
                    )

        return employee

    @staticmethod
    def set_employee_profile_enabled(
        db: Session,
        user: CompanyUser,
        enabled: bool,
        *,
        hire_date_override: date | None = None,
        department: str | None = None,
        job_title: str | None = None,
        salary_base: Decimal | None = None,
        payment_mode: str | None = None,
    ) -> Employee | None:
        employee = EmployeeSyncService._find_employee(db, user)
        if enabled:
            return EmployeeSyncService.sync_company_user(
                db,
                user,
                hire_date_override=hire_date_override,
                department=department,
                job_title=job_title,
                salary_base=salary_base,
                payment_mode=payment_mode,
            )
        if employee is None:
            return None
        employee.status = "INACTIVE"
        employee.notes = EmployeeSyncService._merge_notes(employee.notes, user.id)
        db.flush()
        return employee

    @staticmethod
    def sync_tenant_users(db: Session, tenant_id: UUID | str) -> list[Employee]:
        users = (
            db.execute(
                select(CompanyUser)
                .where(CompanyUser.tenant_id == EmployeeSyncService._db_tenant_id(db, tenant_id))
                .order_by(CompanyUser.created_at.asc())
            )
            .scalars()
            .all()
        )
        synced: list[Employee] = []
        for user in users:
            employee = EmployeeSyncService.sync_company_user(db, user)
            if employee is not None:
                synced.append(employee)
        db.flush()
        return synced
