
from collections import defaultdict
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models import (
    EmpresaModulo,
    ModuloAsignado,
    RolEmpresa,
    UsuarioEmpresa,
    UsuarioRolempresa,
)
from app.modules.usuarios.infrastructure.schemas import UsuarioEmpresaCreate


def get_usuarios_by_empresa(
    db: Session,
    empresa_id: int,
    *,
    include_admins: bool = True,
    include_inactivos: bool = False,
) -> List[UsuarioEmpresa]:
    query = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.empresa_id == empresa_id)
    if not include_admins:
        query = query.filter(UsuarioEmpresa.es_admin_empresa.is_(False))
    if not include_inactivos:
        query = query.filter(UsuarioEmpresa.activo.isnot(False))
    return query.all()


def get_usuario_by_id(db: Session, usuario_id: int, empresa_id: int) -> Optional[UsuarioEmpresa]:
    return (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.id == usuario_id,
            UsuarioEmpresa.empresa_id == empresa_id,
        )
        .first()
    )


def get_usuario_by_email(db: Session, email: str) -> Optional[UsuarioEmpresa]:
    return db.query(UsuarioEmpresa).filter(UsuarioEmpresa.email == email).first()


def get_usuario_by_username(db: Session, username: str) -> Optional[UsuarioEmpresa]:
    return db.query(UsuarioEmpresa).filter(UsuarioEmpresa.username == username).first()


def insert_usuario_empresa(
    db: Session,
    *,
    empresa_id: int,
    data: UsuarioEmpresaCreate,
    hashed_password: str,
) -> UsuarioEmpresa:
    model = UsuarioEmpresa(
        empresa_id=empresa_id,
        nombre_encargado=data.nombre_encargado,
        apellido_encargado=data.apellido_encargado,
        email=data.email,
        username=data.username,
        password_hash=hashed_password,
        activo=data.activo,
        es_admin_empresa=data.es_admin_empresa,
    )
    db.add(model)
    db.flush()
    return model


def set_modulos_usuario(db: Session, usuario_id: int, empresa_id: int, modulos: Iterable[int]) -> None:
    db.query(ModuloAsignado).filter(
        ModuloAsignado.usuario_id == usuario_id,
        ModuloAsignado.empresa_id == empresa_id,
    ).delete(synchronize_session=False)
    for modulo_id in modulos:
        db.add(
            ModuloAsignado(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                modulo_id=modulo_id,
            )
        )


def set_roles_usuario(db: Session, usuario_id: int, empresa_id: int, roles: Iterable[int]) -> None:
    db.query(UsuarioRolempresa).filter(
        UsuarioRolempresa.usuario_id == usuario_id,
        UsuarioRolempresa.empresa_id == empresa_id,
    ).delete(synchronize_session=False)
    for rol_id in roles:
        db.add(
            UsuarioRolempresa(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                rol_id=rol_id,
                activo=True,
            )
        )


def get_modulos_usuario_ids(db: Session, usuario_id: int, empresa_id: int) -> List[int]:
    rows = (
        db.query(ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.usuario_id == usuario_id,
            ModuloAsignado.empresa_id == empresa_id,
        )
        .all()
    )
    return [row[0] for row in rows]


def get_roles_usuario_ids(db: Session, usuario_id: int, empresa_id: int) -> List[int]:
    rows = (
        db.query(UsuarioRolempresa.rol_id)
        .filter(
            UsuarioRolempresa.usuario_id == usuario_id,
            UsuarioRolempresa.empresa_id == empresa_id,
            UsuarioRolempresa.activo.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def get_modulos_contratados_ids(db: Session, empresa_id: int) -> List[int]:
    rows = (
        db.query(EmpresaModulo.modulo_id)
        .filter(
            EmpresaModulo.empresa_id == empresa_id,
            EmpresaModulo.activo.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def count_admins_empresa(db: Session, empresa_id: int) -> int:
    return (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.empresa_id == empresa_id,
            UsuarioEmpresa.es_admin_empresa.is_(True),
            UsuarioEmpresa.activo.isnot(False),
        )
        .count()
    )


def find_super_admin_role_id(db: Session, empresa_id: int) -> Optional[int]:
    return (
        db.query(RolEmpresa.id)
        .filter(
            RolEmpresa.empresa_id == empresa_id,
            RolEmpresa.nombre.ilike('%admin%'),
        )
        .order_by(RolEmpresa.id.asc())
        .scalar()
    )


def load_detalle_usuarios(db: Session, empresa_id: int) -> List[tuple[UsuarioEmpresa, List[int], List[int]]]:
    usuarios = get_usuarios_by_empresa(db, empresa_id, include_admins=True, include_inactivos=True)
    if not usuarios:
        return []

    usuario_ids = [u.id for u in usuarios]
    mod_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, modulo_id in (
        db.query(ModuloAsignado.usuario_id, ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.empresa_id == empresa_id,
            ModuloAsignado.usuario_id.in_(usuario_ids),
        )
        .all()
    ):
        mod_map[usuario_id].append(modulo_id)

    rol_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, rol_id in (
        db.query(UsuarioRolempresa.usuario_id, UsuarioRolempresa.rol_id)
        .filter(
            UsuarioRolempresa.empresa_id == empresa_id,
            UsuarioRolempresa.usuario_id.in_(usuario_ids),
            UsuarioRolempresa.activo.is_(True),
        )
        .all()
    ):
        rol_map[usuario_id].append(rol_id)

    return [(u, mod_map.get(u.id, []), rol_map.get(u.id, [])) for u in usuarios]


def get_modulos_contratados(db: Session, empresa_id: int) -> List[dict]:
    rows = (
        db.query(EmpresaModulo)
        .filter(
            EmpresaModulo.empresa_id == empresa_id,
            EmpresaModulo.activo.is_(True),
        )
        .all()
    )
    result: List[dict] = []
    for row in rows:
        modulo = row.modulo
        result.append(
            dict(
                id=row.modulo_id,
                nombre=getattr(modulo, "nombre", None),
                categoria=getattr(modulo, "categoria", None),
                icono=getattr(modulo, "icono", None),
            )
        )
    return result


def get_roles_empresa(db: Session, empresa_id: int) -> List[dict]:
    rows = (
        db.query(RolEmpresa)
        .filter(RolEmpresa.empresa_id == empresa_id)
        .order_by(RolEmpresa.nombre.asc())
        .all()
    )
    return [dict(id=row.id, nombre=row.nombre, descripcion=row.descripcion) for row in rows]

