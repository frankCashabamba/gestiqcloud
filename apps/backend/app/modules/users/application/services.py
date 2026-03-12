from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import CompanyUser
from app.modules.hr.application.compensation import (
    current_payment_mode,
    current_salary_amount,
    payment_mode_to_api,
)
from app.modules.hr.application.employee_sync_service import EmployeeSyncService
from app.modules.users.application import validators as val
from app.modules.users.domain.models import CompanyUserAggregate
from app.modules.users.infrastructure import repositories as repo
from app.modules.users.infrastructure.schemas import (
    CompanyRoleOption,
    CompanyUserCreate,
    CompanyUserOut,
    CompanyUserUpdate,
    ModuleOption,
)


def _employee_sync_kwargs(data: CompanyUserCreate | CompanyUserUpdate) -> dict:
    return {
        "hire_date_override": data.employee_hire_date,
        "department": data.employee_department,
        "job_title": data.employee_job_title,
        "salary_base": data.employee_salary_base,
        "payment_mode": data.employee_payment_mode,
    }


def _employee_profile(db: Session, user: CompanyUser) -> dict:
    employee = EmployeeSyncService._find_employee(db, user)
    if employee is None:
        return {
            "as_employee": False,
            "employee_hire_date": None,
            "employee_department": None,
            "employee_job_title": None,
            "employee_salary_base": None,
            "employee_payment_mode": None,
        }
    salary = current_salary_amount(employee)
    return {
        "as_employee": True,
        "employee_hire_date": employee.hire_date,
        "employee_department": employee.department,
        "employee_job_title": employee.job_title,
        "employee_salary_base": salary,
        "employee_payment_mode": payment_mode_to_api(current_payment_mode(employee)),
    }


def _aggregate(user: CompanyUser, modules: list[int], roles: list[int]) -> CompanyUserAggregate:
    return CompanyUserAggregate(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        is_company_admin=user.is_company_admin,
        is_active=user.is_active,
        modules=modules,
        roles=roles,
        last_login_at=user.last_login_at,
    )


def _to_schema(agg: CompanyUserAggregate, **employee_profile) -> CompanyUserOut:
    return CompanyUserOut(
        id=agg.id,
        tenant_id=agg.tenant_id,
        email=agg.email,
        first_name=agg.first_name,
        last_name=agg.last_name,
        username=agg.username,
        is_company_admin=agg.is_company_admin,
        active=agg.is_active,
        as_employee=employee_profile.get("as_employee", False),
        employee_hire_date=employee_profile.get("employee_hire_date"),
        employee_department=employee_profile.get("employee_department"),
        employee_job_title=employee_profile.get("employee_job_title"),
        employee_salary_base=employee_profile.get("employee_salary_base"),
        employee_payment_mode=employee_profile.get("employee_payment_mode"),
        modules=agg.modules,
        roles=agg.roles,
        last_login_at=agg.last_login_at,
    )


def list_company_users(
    db: Session, tenant_id: int, include_inactive: bool = True
) -> list[CompanyUserOut]:
    detalles = repo.load_user_details(db, tenant_id)
    result: list[CompanyUserOut] = []
    for usuario, modulos, roles in detalles:
        if not include_inactive and not usuario.is_active:
            continue
        agg = _aggregate(usuario, modulos, roles)
        result.append(_to_schema(agg, **_employee_profile(db, usuario)))
    return result


def get_company_user(db: Session, tenant_id: int, usuario_id: int) -> CompanyUserOut:
    usuario = repo.get_user_by_id(db, usuario_id, tenant_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="user_not_found")
    agg = _aggregate(
        usuario,
        repo.get_user_module_ids(db, usuario.id, tenant_id),
        repo.get_user_role_ids(db, usuario.id, tenant_id),
    )
    return _to_schema(agg, **_employee_profile(db, usuario))


def create_company_user(
    db: Session,
    tenant_id: int,
    data: CompanyUserCreate,
    *,
    asignado_por_id: int | None = None,
) -> CompanyUserOut:
    val.ensure_email_unique(db, data.email)
    val.ensure_username_unique(db, data.username)

    modules = list(data.modules)
    roles = list(data.roles)
    if data.is_company_admin:
        modules = repo.get_contracted_module_ids(db, tenant_id)
        if not roles:
            super_role_id = repo.find_super_admin_role_id(db, tenant_id)
            if super_role_id:
                roles = [super_role_id]
    else:
        val.validate_contracted_modules(db, tenant_id, modules)

    hashed_password = get_password_hash(data.password)

    usuario = repo.insert_company_user(
        db,
        tenant_id=tenant_id,
        data=data,
        hashed_password=hashed_password,
    )

    repo.set_user_modules(db, usuario.id, tenant_id, modules)
    repo.set_user_roles(db, usuario.id, tenant_id, roles)
    if data.as_employee:
        EmployeeSyncService.set_employee_profile_enabled(
            db,
            usuario,
            True,
            **_employee_sync_kwargs(data),
        )

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_user_module_ids(db, usuario.id, tenant_id),
        repo.get_user_role_ids(db, usuario.id, tenant_id),
    )
    return _to_schema(agg, **_employee_profile(db, usuario))


def update_company_user(
    db: Session,
    tenant_id: int,
    usuario_id: int,
    data: CompanyUserUpdate,
) -> CompanyUserOut:
    usuario = repo.get_user_by_id(db, usuario_id, tenant_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="user_not_found")

    if data.email and data.email != usuario.email:
        val.ensure_email_unique(db, data.email, exclude_user_id=usuario.id)
        usuario.email = data.email

    if data.username is not None and data.username != usuario.username:
        val.ensure_username_unique(db, data.username, exclude_user_id=usuario.id)
        usuario.username = data.username

    if data.first_name is not None:
        usuario.first_name = data.first_name
    if data.last_name is not None:
        usuario.last_name = data.last_name

    if data.password:
        usuario.password_hash = get_password_hash(data.password)

    if data.active is not None and data.active is False:
        val.ensure_not_last_admin(db, tenant_id, user_id=usuario.id)
        usuario.is_active = False
    elif data.active is not None:
        usuario.is_active = data.active

    if data.is_company_admin is not None:
        if not data.is_company_admin and usuario.is_company_admin:
            val.ensure_not_last_admin(db, tenant_id, user_id=usuario.id)
        usuario.is_company_admin = data.is_company_admin

    if usuario.is_company_admin:
        # Admins always hold every contracted module
        modules = repo.get_contracted_module_ids(db, tenant_id)
        repo.set_user_modules(db, usuario.id, tenant_id, modules)
    elif data.modules is not None:
        val.validate_contracted_modules(db, tenant_id, data.modules)
        repo.set_user_modules(db, usuario.id, tenant_id, data.modules)

    if data.roles is not None:
        repo.set_user_roles(db, usuario.id, tenant_id, data.roles)
    if data.as_employee is not None:
        EmployeeSyncService.set_employee_profile_enabled(
            db,
            usuario,
            data.as_employee,
            **_employee_sync_kwargs(data),
        )

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_user_module_ids(db, usuario.id, tenant_id),
        repo.get_user_role_ids(db, usuario.id, tenant_id),
    )
    return _to_schema(agg, **_employee_profile(db, usuario))


def toggle_user_active(
    db: Session, tenant_id: int, usuario_id: int, active: bool
) -> CompanyUserOut:
    payload = CompanyUserUpdate(active=active)
    return update_company_user(db, tenant_id, usuario_id, payload)


def check_username_availability(db: Session, username: str) -> bool:
    return repo.get_user_by_username(db, username) is None


def list_company_modules(db: Session, tenant_id: int) -> list[ModuleOption]:
    rows = repo.get_contracted_modules(db, tenant_id)
    return [ModuleOption(**row) for row in rows]


def list_company_roles(db: Session, tenant_id: int) -> list[CompanyRoleOption]:
    rows = repo.get_company_roles(db, tenant_id)
    return [CompanyRoleOption(**row) for row in rows]
