"""Module: role_service.py

Auto-generated module docstring."""

# services/role_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import RolEmpresa, UsuarioRolempresa


async def get_user_permisos(usuario_id: int, tenant_id: int, db: AsyncSession) -> list[str]:
    query = (
        select(RolEmpresa.permisos)
        .join(UsuarioRolempresa, RolEmpresa.id == UsuarioRolempresa.rol_id)
        .where(
            UsuarioRolempresa.usuario_id == usuario_id,
            UsuarioRolempresa.tenant_id == tenant_id,
            UsuarioRolempresa.active,
        )
        .limit(1)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        return []
    permisos_dict = row[0] or {}
    return [perm for perm, permitido in permisos_dict.items() if permitido]
