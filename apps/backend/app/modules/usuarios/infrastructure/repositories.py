from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models import AssignedModule, CompanyModule, CompanyRole, CompanyUser, CompanyUserRole
from app.modules.usuarios.infrastructure.schemas import UsuarioEmpresaCreate


def get_usuarios_by_empresa(
    db: Session,
    tenant_id: int,
    *,
    include_admins: bool = True,
    include_inactivos: bool = False,
) -> list[CompanyUser]:
    query = db.query(CompanyUser).filter(CompanyUser.tenant_id == tenant_id)
    if not include_admins:
        query = query.filter(CompanyUser.es_admin_empresa.is_(False))
    if not include_inactivos:
        query = query.filter(CompanyUser.activo.isnot(False))
    return query.all()


def get_usuario_by_id(db: Session, usuario_id: int, tenant_id: int) -> CompanyUser | None:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.id == usuario_id,
            CompanyUser.tenant_id == tenant_id,
        )
        .first()
    )


def get_usuario_by_email(db: Session, email: str) -> CompanyUser | None:
    return db.query(CompanyUser).filter(CompanyUser.email == email).first()


def get_usuario_by_username(db: Session, username: str) -> CompanyUser | None:
    return db.query(CompanyUser).filter(CompanyUser.username == username).first()


def insert_usuario_empresa(
    db: Session,
    *,
    tenant_id: int,
    data: UsuarioEmpresaCreate,
    hashed_password: str,
) -> CompanyUser:
    model = CompanyUser(
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


def set_modulos_usuario(db: Session, usuario_id, tenant_id, modulos: Iterable) -> None:
    db.query(AssignedModule).filter(
        AssignedModule.usuario_id == usuario_id,
        AssignedModule.tenant_id == tenant_id,
    ).delete(synchronize_session=False)
    for modulo_id in modulos:
        db.add(
            AssignedModule(
                usuario_id=usuario_id,
                tenant_id=tenant_id,
                modulo_id=modulo_id,
            )
        )


def set_roles_usuario(db: Session, usuario_id, tenant_id, roles: Iterable) -> None:
    db.query(CompanyUserRole).filter(
        CompanyUserRole.usuario_id == usuario_id,
        CompanyUserRole.tenant_id == tenant_id,
    ).delete(synchronize_session=False)
    for rol_id in roles:
        db.add(
            CompanyUserRole(
                usuario_id=usuario_id,
                tenant_id=tenant_id,
                rol_id=rol_id,
                activo=True,
            )
        )


def get_modulos_usuario_ids(db: Session, usuario_id, tenant_id):
    rows = (
        db.query(AssignedModule.modulo_id)
        .filter(
            AssignedModule.usuario_id == usuario_id,
            AssignedModule.tenant_id == tenant_id,
        )
        .all()
    )
    return [row[0] for row in rows]


def get_roles_usuario_ids(db: Session, usuario_id, tenant_id):
    rows = (
        db.query(CompanyUserRole.rol_id)
        .filter(
            CompanyUserRole.usuario_id == usuario_id,
            CompanyUserRole.tenant_id == tenant_id,
            CompanyUserRole.activo.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def get_modulos_contratados_ids(db: Session, tenant_id: int):
    rows = (
        db.query(CompanyModule.modulo_id)
        .filter(
            CompanyModule.tenant_id == tenant_id,
            CompanyModule.active.is_(True),
        )
        .all()
    )
    return [row[0] for row in rows]


def count_admins_empresa(db: Session, tenant_id: int) -> int:
    return (
        db.query(CompanyUser)
        .filter(
            CompanyUser.tenant_id == tenant_id,
            CompanyUser.es_admin_empresa.is_(True),
            CompanyUser.activo.isnot(False),
        )
        .count()
    )


def find_super_admin_role_id(db: Session, tenant_id: int):
    return (
        db.query(CompanyRole.id)
        .filter(
            CompanyRole.tenant_id == tenant_id,
            CompanyRole.name.ilike("%admin%"),
        )
        .order_by(CompanyRole.id.asc())
        .scalar()
    )


def load_detalle_usuarios(
    db: Session, tenant_id: int
) -> list[tuple[CompanyUser, list[int], list[int]]]:
    usuarios = get_usuarios_by_empresa(db, tenant_id, include_admins=True, include_inactivos=True)
    if not usuarios:
        return []

    usuario_ids = [u.id for u in usuarios]
    mod_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, modulo_id in (
        db.query(AssignedModule.usuario_id, AssignedModule.modulo_id)
        .filter(
            AssignedModule.tenant_id == tenant_id,
            AssignedModule.usuario_id.in_(usuario_ids),
        )
        .all()
    ):
        mod_map[usuario_id].append(modulo_id)

    rol_map: dict[int, list[int]] = defaultdict(list)
    for usuario_id, rol_id in (
        db.query(CompanyUserRole.usuario_id, CompanyUserRole.rol_id)
        .filter(
            CompanyUserRole.tenant_id == tenant_id,
            CompanyUserRole.usuario_id.in_(usuario_ids),
            CompanyUserRole.activo.is_(True),
        )
        .all()
    ):
        rol_map[usuario_id].append(rol_id)

    return [(u, mod_map.get(u.id, []), rol_map.get(u.id, [])) for u in usuarios]


def get_modulos_contratados(db: Session, tenant_id: int) -> list[dict]:
    rows = (
        db.query(CompanyModule)
        .filter(
            CompanyModule.tenant_id == tenant_id,
            CompanyModule.active.is_(True),
        )
        .all()
    )
    result: list[dict] = []
    for row in rows:
        modulo = row.modulo
        result.append(
            {
                "id": row.modulo_id,
                "name": getattr(modulo, "name", None),
                "categoria": getattr(modulo, "categoria", None),
                "icono": getattr(modulo, "icono", None),
            }
        )
    return result


def get_roles_empresa(db: Session, tenant_id: int) -> list[dict]:
    rows = (
        db.query(CompanyRole)
        .filter(CompanyRole.tenant_id == tenant_id)
        .order_by(CompanyRole.name.asc())
        .all()
    )
    return [{"id": row.id, "name": row.name, "description": row.description} for row in rows]
