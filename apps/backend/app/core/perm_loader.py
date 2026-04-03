# app/core/perm_loader.py
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.config.database import temp_rls_bypass
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
        # Usuario regular: cargar permisos desde todos los roles activos.
        # Se usa temp_rls_bypass porque company_user_roles tiene FORCE RLS
        # y las GUCs pueden no estar activas (ej. si hubo rollback previo)
        # o los registros pueden tener tenant_id=NULL (creados antes del RLS).
        try:
            with temp_rls_bypass(db):
                relaciones = (
                    db.query(CompanyUserRole)
                    .filter(
                        CompanyUserRole.user_id == user.id,
                        or_(
                            CompanyUserRole.tenant_id == user.tenant_id,
                            CompanyUserRole.tenant_id.is_(None),
                        ),
                        CompanyUserRole.is_active.is_(True),
                    )
                    .all()
                )

                for relacion_rol in relaciones:
                    rol = (
                        db.query(CompanyRole).filter(CompanyRole.id == relacion_rol.role_id).first()
                    )
                    if rol and isinstance(rol.permissions, dict):
                        for k, v in rol.permissions.items():
                            if isinstance(v, dict) and isinstance(permisos.get(k), dict):
                                # merge granular: { "hr": { "read": true } }
                                permisos[k] = {**permisos[k], **v}
                            else:
                                permisos[k] = v
        except Exception:
            # Si la tabla no existe o hay error, usuario sin permisos de rol
            pass

    # Permisos automáticos por módulos asignados (auto_view_module)
    with temp_rls_bypass(db):
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

    # Normalizar permisos al formato { "module": { "action": True } }
    # Casos:
    #   { "pos.read": True }  → pasar tal cual (frontend lo descompone por punto)
    #   { "pos": True }       → expandir a { "pos": { "read": True } }
    #   { "hr": { "read": True } } → pasar tal cual
    permisos_norm: dict[str, Any] = {}
    for k, v in {**permisos, **permisos_modulos}.items():
        if isinstance(v, dict):
            permisos_norm[k] = v
        elif v is True:
            if "." in k or ":" in k:
                # Ya tiene formato modulo.accion — el frontend lo normaliza
                permisos_norm[k] = v
            else:
                # Flat sin acción → grant read por defecto
                permisos_norm[k] = {"read": True}
        # False/None se descartan
    permisos_finales: dict[str, Any] = permisos_norm

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
