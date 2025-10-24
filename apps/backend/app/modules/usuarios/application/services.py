
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models import UsuarioEmpresa
from app.modules.usuarios.application import validators as val
from app.modules.usuarios.domain.models import UsuarioEmpresaAggregate
from app.modules.usuarios.infrastructure import repositories as repo
from app.modules.usuarios.infrastructure.schemas import (
    UsuarioEmpresaCreate,
    UsuarioEmpresaOut,
    UsuarioEmpresaUpdate,
    ModuloOption,
    RolEmpresaOption,
)


def _aggregate(usuario: UsuarioEmpresa, modulos: list[int], roles: list[int]) -> UsuarioEmpresaAggregate:
    return UsuarioEmpresaAggregate(
        id=usuario.id,
        empresa_id=usuario.empresa_id,
        email=usuario.email,
        nombre_encargado=usuario.nombre_encargado,
        apellido_encargado=usuario.apellido_encargado,
        username=usuario.username,
        es_admin_empresa=usuario.es_admin_empresa,
        activo=usuario.activo,
        modulos=modulos,
        roles=roles,
        ultimo_login_at=usuario.last_login_at,
    )


def _to_schema(agg: UsuarioEmpresaAggregate) -> UsuarioEmpresaOut:
    return UsuarioEmpresaOut(
        id=agg.id,
        empresa_id=agg.empresa_id,
        email=agg.email,
        nombre_encargado=agg.nombre_encargado,
        apellido_encargado=agg.apellido_encargado,
        username=agg.username,
        es_admin_empresa=agg.es_admin_empresa,
        activo=agg.activo,
        modulos=agg.modulos,
        roles=agg.roles,
        ultimo_login_at=agg.ultimo_login_at,
    )


def listar_usuarios_empresa(db: Session, empresa_id: int, include_inactivos: bool = True) -> List[UsuarioEmpresaOut]:
    detalles = repo.load_detalle_usuarios(db, empresa_id)
    result: list[UsuarioEmpresaOut] = []
    for usuario, modulos, roles in detalles:
        if not include_inactivos and not usuario.activo:
            continue
        agg = _aggregate(usuario, modulos, roles)
        result.append(_to_schema(agg))
    return result


def crear_usuario_empresa(
    db: Session,
    empresa_id: int,
    data: UsuarioEmpresaCreate,
    *,
    asignado_por_id: int | None = None,
) -> UsuarioEmpresaOut:
    val.ensure_email_unique(db, data.email)
    val.ensure_username_unique(db, data.username)

    modulos = list(data.modulos)
    roles = list(data.roles)
    if data.es_admin_empresa:
        modulos = repo.get_modulos_contratados_ids(db, empresa_id)
        if not roles:
            super_role_id = repo.find_super_admin_role_id(db, empresa_id)
            if super_role_id:
                roles = [super_role_id]
    else:
        val.validate_modulos_contratados(db, empresa_id, modulos)

    hashed_password = get_password_hash(data.password)

    usuario = repo.insert_usuario_empresa(
        db,
        empresa_id=empresa_id,
        data=data,
        hashed_password=hashed_password,
    )

    repo.set_modulos_usuario(db, usuario.id, empresa_id, modulos)
    repo.set_roles_usuario(db, usuario.id, empresa_id, roles)

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_modulos_usuario_ids(db, usuario.id, empresa_id),
        repo.get_roles_usuario_ids(db, usuario.id, empresa_id),
    )
    return _to_schema(agg)


def actualizar_usuario_empresa(
    db: Session,
    empresa_id: int,
    usuario_id: int,
    data: UsuarioEmpresaUpdate,
) -> UsuarioEmpresaOut:
    usuario = repo.get_usuario_by_id(db, usuario_id, empresa_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.email and data.email != usuario.email:
        val.ensure_email_unique(db, data.email, exclude_usuario_id=usuario.id)
        usuario.email = data.email

    if data.username is not None and data.username != usuario.username:
        val.ensure_username_unique(db, data.username, exclude_usuario_id=usuario.id)
        usuario.username = data.username

    if data.nombre_encargado is not None:
        usuario.nombre_encargado = data.nombre_encargado
    if data.apellido_encargado is not None:
        usuario.apellido_encargado = data.apellido_encargado

    if data.password:
        usuario.password_hash = get_password_hash(data.password)

    if data.activo is not None and data.activo is False:
        val.ensure_not_last_admin(db, empresa_id, usuario_id=usuario.id)
        usuario.activo = False
    elif data.activo is not None:
        usuario.activo = data.activo

    if data.es_admin_empresa is not None:
        if not data.es_admin_empresa and usuario.es_admin_empresa:
            val.ensure_not_last_admin(db, empresa_id, usuario_id=usuario.id)
        usuario.es_admin_empresa = data.es_admin_empresa

    if usuario.es_admin_empresa:
        # Los administradores siempre tienen todos los módulos contratados
        modulos = repo.get_modulos_contratados_ids(db, empresa_id)
        repo.set_modulos_usuario(db, usuario.id, empresa_id, modulos)
    elif data.modulos is not None:
        val.validate_modulos_contratados(db, empresa_id, data.modulos)
        repo.set_modulos_usuario(db, usuario.id, empresa_id, data.modulos)

    if data.roles is not None:
        repo.set_roles_usuario(db, usuario.id, empresa_id, data.roles)

    db.commit()
    db.refresh(usuario)

    agg = _aggregate(
        usuario,
        repo.get_modulos_usuario_ids(db, usuario.id, empresa_id),
        repo.get_roles_usuario_ids(db, usuario.id, empresa_id),
    )
    return _to_schema(agg)


def toggle_usuario_activo(db: Session, empresa_id: int, usuario_id: int, activo: bool) -> UsuarioEmpresaOut:
    payload = UsuarioEmpresaUpdate(activo=activo)
    return actualizar_usuario_empresa(db, empresa_id, usuario_id, payload)


def check_username_availability(db: Session, username: str) -> bool:
    return repo.get_usuario_by_username(db, username) is None


def listar_modulos_empresa(db: Session, empresa_id: int) -> List[ModuloOption]:
    rows = repo.get_modulos_contratados(db, empresa_id)
    return [ModuloOption(**row) for row in rows]


def listar_roles_empresa(db: Session, empresa_id: int) -> List[RolEmpresaOption]:
    rows = repo.get_roles_empresa(db, empresa_id)
    return [RolEmpresaOption(**row) for row in rows]
