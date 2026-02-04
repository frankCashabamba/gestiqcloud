# app/core/perm_loader.py
from typing import Any

from sqlalchemy.orm import Session

from app.models.company.company_role import CompanyRole
from app.models.company.company_user import CompanyUser
from app.models.company.company_user_role import CompanyUserRole
from app.models.core.module import AssignedModule, Module
from app.models.tenant import Tenant


def build_tenant_claims(db: Session, user: CompanyUser) -> dict[str, Any]:
    # Tenant: prioriza relación ya cargada
    tenant = getattr(user, "tenant", None)
    if tenant is None and user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        # Deja que el login falle fuera con invalid_credentials
        return {}

    # Permisos: Admin de empresa tiene acceso completo
    permisos: dict[str, Any] = {}

    if getattr(user, "is_company_admin", False):
        # Admin de empresa: permisos completos
        permisos = {
            "admin": True,
            "write": True,
            "read": True,
            "delete": True,
            "manage_users": True,
            "manage_settings": True,
            "manage_roles": True,
            "manage_modules": True,
            "view_reports": True,
            "export_data": True,
        }
    else:
        # Usuario regular: cargar permisos desde roles
        try:
            relacion_rol = (
                db.query(CompanyUserRole)
                .filter(CompanyUserRole.user_id == user.id, CompanyUserRole.is_active.is_(True))
                .first()
            )

            if relacion_rol:
                rol = db.query(CompanyRole).filter(CompanyRole.id == relacion_rol.role_id).first()
                if rol and isinstance(rol.permissions, dict):
                    permisos = dict(rol.permissions)  # copy defensivo
        except Exception:
            # Si la tabla no existe o hay error, usuario sin permisos de rol
            pass

    # Permisos automáticos por módulos asignados (auto_view_module)
    modulos_asignados = (
        db.query(AssignedModule)
        .join(Module, Module.id == AssignedModule.module_id)
        .filter(
            AssignedModule.user_id == user.id,
            AssignedModule.tenant_id == user.tenant_id,
            AssignedModule.auto_view_module == True,  # noqa
        )
        .all()
    )
    permisos_modulos = {f"ver_{m.module.url}": True for m in modulos_asignados}

    permisos_finales: dict[str, Any] = {**permisos, **permisos_modulos}

    plantilla = getattr(tenant, "plantilla_inicio", None) or "DefaultPlantilla"

    claims = {
        "user_id": str(user.id),
        # Compat: varios endpoints esperan 'tenant_user_id'
        "tenant_user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "empresa_slug": tenant.slug,
        "plantilla": plantilla,
        "is_company_admin": bool(getattr(user, "is_company_admin", False)),
        "name": getattr(user, "nombre_encargado", None),
        "roles": [],  # add role names if available
        "permissions": permisos_finales,
        "kind": "tenant",
        "sub": user.email,
    }
    return claims
