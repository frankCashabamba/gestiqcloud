# app/core/perm_loader.py
from typing import Any

from sqlalchemy.orm import Session

from app.models.core.modulo import Modulo, ModuloAsignado
from app.models.empresa.rolempresas import RolEmpresa
from app.models.empresa.usuario_rolempresa import UsuarioRolempresa
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.models.tenant import Tenant


def build_tenant_claims(db: Session, user: UsuarioEmpresa) -> dict[str, Any]:
    # Tenant: prioriza relación ya cargada
    tenant = getattr(user, "tenant", None)
    if tenant is None and user.tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).first()
    if not tenant:
        # Deja que el login falle fuera con invalid_credentials
        return {}

    # Permisos: Admin de empresa tiene acceso completo
    permisos: dict[str, Any] = {}

    if getattr(user, "es_admin_empresa", False):
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
                db.query(UsuarioRolempresa).filter_by(usuario_id=user.id, activo=True).first()
            )

            if relacion_rol:
                rol = db.query(RolEmpresa).filter_by(id=relacion_rol.rol_id).first()
                if rol and isinstance(rol.permissions, dict):
                    permisos = dict(rol.permissions)  # copy defensivo
        except Exception:
            # Si la tabla no existe o hay error, usuario sin permisos de rol
            pass

    # Permisos automáticos por módulos asignados (ver_modulo_auto)
    modulos_asignados = (
        db.query(ModuloAsignado)
        .join(Modulo, Modulo.id == ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.usuario_id == user.id,
            ModuloAsignado.tenant_id == user.tenant_id,
            ModuloAsignado.ver_modulo_auto == True,  # noqa
        )
        .all()
    )
    permisos_modulos = {f"ver_{m.modulo.url}": True for m in modulos_asignados}

    permisos_finales: dict[str, Any] = {**permisos, **permisos_modulos}

    plantilla = getattr(tenant, "plantilla_inicio", None) or "DefaultPlantilla"

    claims = {
        "user_id": str(user.id),
        # Compat: varios endpoints esperan 'tenant_user_id'
        "tenant_user_id": str(user.id),
        "tenant_id": str(tenant.id),
        "empresa_slug": tenant.slug,
        "plantilla": plantilla,
        "es_admin_empresa": bool(getattr(user, "es_admin_empresa", False)),
        "nombre": getattr(user, "nombre_encargado", None),
        "roles": [],  # si tienes nombres de rol, puedes añadirlos aquí
        "permisos": permisos_finales,
        "kind": "tenant",
        "sub": user.email,
    }
    return claims
