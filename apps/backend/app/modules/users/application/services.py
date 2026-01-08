from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import CompanyUser
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


def _to_schema(agg: CompanyUserAggregate) -> CompanyUserOut:
    return CompanyUserOut(
        id=agg.id,
        tenant_id=agg.tenant_id,
        email=agg.email,
        first_name=agg.first_name,
        last_name=agg.last_name,
        username=agg.username,
        is_company_admin=agg.is_company_admin,
        active=agg.is_active,
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
        result.append(_to_schema(agg))
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
    return _to_schema(agg)


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

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_user_module_ids(db, usuario.id, tenant_id),
        repo.get_user_role_ids(db, usuario.id, tenant_id),
    )
    return _to_schema(agg)


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

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_user_module_ids(db, usuario.id, tenant_id),
        repo.get_user_role_ids(db, usuario.id, tenant_id),
    )
    return _to_schema(agg)


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
