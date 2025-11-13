from collections import defaultdict
from collections.abc import Iterable

from app.models import EmpresaModulo, ModuloAsignado, RolEmpresa, UsuarioEmpresa, UsuarioRolempresa
from app.modules.usuarios.infrastructure.schemas import UsuarioEmpresaCreate
from sqlalchemy.orm import Session


def get_usuarios_by_empresa(
    db: Session,
    tenant_id: int,
    *,
    include_admins: bool = True,
    include_inactivos: bool = False,
) -> list[UsuarioEmpresa]:
    query = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.tenant_id == tenant_id)
    if not include_admins:
        query = query.filter(UsuarioEmpresa.es_admin_empresa.is_(False))
    if not include_inactivos:
        query = query.filter(UsuarioEmpresa.active.isnot(False))
    return query.all()


def get_usuario_by_id(db: Session, usuario_id: int, tenant_id: int) -> UsuarioEmpresa | None:
    return (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.id == usuario_id,
            UsuarioEmpresa.tenant_id == tenant_id,
        )
        .first()
    )


def get_usuario_by_email(db: Session, email: str) -> UsuarioEmpresa | None:
    return db.query(UsuarioEmpresa).filter(UsuarioEmpresa.email == email).first()


def get_usuario_by_username(db: Session, username: str) -> UsuarioEmpresa | None:
    return db.query(UsuarioEmpresa).filter(UsuarioEmpresa.username == username).first()


def insert_usuario_empresa(
    db: Session,
    *,
    tenant_id: int,
    data: UsuarioEmpresaCreate,
    hashed_password: str,
) -> UsuarioEmpresa:
    model = UsuarioEmpresa(
        tenant_id=tenant_id,
        nombre_encargado=data.nombre_encargado,
        apellido_encargado=data.apellido_encargado,
        email=data.email,
        username=data.username,
        password_hash=hashed_password,
        activo=data.active,
        es_admin_empresa=data.es_admin_empresa,
    )
    db.add(model)
    db.flush()
    return model


def set_modulos_usuario(
    db: Session, usuario_id: int, tenant_id: int, modulos: Iterable[int]
) -> None:
    db.query(ModuloAsignado).filter(
        ModuloAsignado.usuario_id == usuario_id,
        ModuloAsignado.tenant_id == tenant_id,
    ).delete(synchronize_session=False)
    for modulo_id in modulos:
        db.add(
            ModuloAsignado(
                usuario_id=usuario_id,
                tenant_id=tenant_id,
                modulo_id=modulo_id,
            )
        )


def set_roles_usuario(db: Session, usuario_id: int, tenant_id: int, roles: Iterable[int]) -> None:
    db.query(UsuarioRolempresa).filter(
        UsuarioRolempresa.usuario_id == usuario_id,
        UsuarioRolempresa.tenant_id == tenant_id,
    ).delete(synchronize_session=False)
    for rol_id in roles:
        db.add(
            UsuarioRolempresa(
                usuario_id=usuario_id,
                tenant_id=tenant_id,
                rol_id=rol_id,
                activo=True,
            )
        )


def get_modulos_usuario_ids(db: Session, usuario_id: int, tenant_id: int) -> list[int]:
    rows = (
        db.query(ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.usuario_id == usuario_id,
            ModuloAsignado.tenant_id == tenant_id,
        )
        .all()
    )
    return [row[0] for row in rows]


def get_roles_usuario_ids(db: Session, usuario_id: int, tenant_id: int) -> list[int]:
    rows = (
        db.query(UsuarioRolempresa.rol_id)
        .filter(
            UsuarioRolempresa.usuario_id == usuario_id,
            UsuarioRolempresa.tenant_id == tenant_id,
            UsuarioRolempresa.active.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def get_modulos_contratados_ids(db: Session, tenant_id: int) -> list[int]:
    rows = (
        db.query(EmpresaModulo.modulo_id)
        .filter(
            EmpresaModulo.tenant_id == tenant_id,
            EmpresaModulo.active.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def count_admins_empresa(db: Session, tenant_id: int) -> int:
    return (
        db.query(UsuarioEmpresa)
        .filter(
            UsuarioEmpresa.tenant_id == tenant_id,
            UsuarioEmpresa.es_admin_empresa.is_(True),
            UsuarioEmpresa.active.isnot(False),
        )
        .count()
    )


def find_super_admin_role_id(db: Session, tenant_id: int) -> int | None:
    return (
        db.query(RolEmpresa.id)
        .filter(
            RolEmpresa.tenant_id == tenant_id,
            RolEmpresa.name.ilike("%admin%"),
        )
        .order_by(RolEmpresa.id.asc())
        .scalar()
    )


def load_detalle_usuarios(
    db: Session, tenant_id: int
) -> list[tuple[UsuarioEmpresa, list[int], list[int]]]:
    usuarios = get_usuarios_by_empresa(db, tenant_id, include_admins=True, include_inactivos=True)
    if not usuarios:
        return []

    usuario_ids = [u.id for u in usuarios]
    mod_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, modulo_id in (
        db.query(ModuloAsignado.usuario_id, ModuloAsignado.modulo_id)
        .filter(
            ModuloAsignado.tenant_id == tenant_id,
            ModuloAsignado.usuario_id.in_(usuario_ids),
        )
        .all()
    ):
        mod_map[usuario_id].append(modulo_id)

    rol_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, rol_id in (
        db.query(UsuarioRolempresa.usuario_id, UsuarioRolempresa.rol_id)
        .filter(
            UsuarioRolempresa.tenant_id == tenant_id,
            UsuarioRolempresa.usuario_id.in_(usuario_ids),
            UsuarioRolempresa.active.is_(True),
        )
        .all()
    ):
        rol_map[usuario_id].append(rol_id)

    return [(u, mod_map.get(u.id, []), rol_map.get(u.id, [])) for u in usuarios]


def get_modulos_contratados(db: Session, tenant_id: int) -> list[dict]:
    rows = (
        db.query(EmpresaModulo)
        .filter(
            EmpresaModulo.tenant_id == tenant_id,
            EmpresaModulo.active.is_(True),
        )
        .all()
    )
    result: list[dict] = []
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


def get_roles_empresa(db: Session, tenant_id: int) -> list[dict]:
    rows = (
        db.query(RolEmpresa)
        .filter(RolEmpresa.tenant_id == tenant_id)
        .order_by(RolEmpresa.name.asc())
        .all()
    )
    return [dict(id=row.id, nombre=row.name, descripcion=row.description) for row in rows]
