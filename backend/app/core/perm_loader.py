# app/core/perm_loader.py
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.models.empresa.empresa import Empresa
from app.models.empresa.rolempresas import RolEmpresa
from app.models.empresa.usuario_rolempresa import UsuarioRolempresa
from app.models.core.modulo import Modulo, ModuloAsignado

def build_tenant_claims(db: Session, user: UsuarioEmpresa) -> Dict[str, Any]:
    # Empresa
    empresa = db.query(Empresa).filter(Empresa.id == user.empresa_id).first()
    if not empresa:
        # deja que el login falle fuera con 404 company_not_found
        return {}

    # Rol activo
    relacion_rol = (
        db.query(UsuarioRolempresa)
        .filter_by(usuario_id=user.id, activo=True)
        .first()
    )

    permisos: Dict[str, Any] = {}
    if relacion_rol:
        rol = db.query(RolEmpresa).filter_by(id=relacion_rol.rol_id).first()
        if rol and isinstance(rol.permisos, dict):
            permisos = dict(rol.permisos)  # copy defensivo

    # Permisos automáticos por módulos asignados (ver_modulo_auto)
    modulos_asignados = (
        db.query(ModuloAsignado)
        .join(Modulo, Modulo.id == ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.usuario_id == user.id,
            ModuloAsignado.empresa_id == user.empresa_id,
            ModuloAsignado.ver_modulo_auto == True,  # noqa
        )
        .all()
    )
    permisos_modulos = {f"ver_{m.modulo.url}": True for m in modulos_asignados}

    permisos_finales: Dict[str, Any] = {**permisos, **permisos_modulos}

    plantilla = empresa.plantilla_inicio or "DefaultPlantilla"

    claims = {
        "user_id": str(user.id),
        "tenant_id": str(empresa.id),
        "empresa_slug": empresa.slug,
        "plantilla": plantilla,
        "es_admin_empresa": bool(getattr(user, "es_admin_empresa", False)),
        "nombre": getattr(user, "nombre_encargado", None),
        "roles": [],           # si tienes nombres de rol, puedes añadirlos aquí
        "permisos": permisos_finales,
        "kind": "tenant",
        "sub": user.email,
    }
    return claims
