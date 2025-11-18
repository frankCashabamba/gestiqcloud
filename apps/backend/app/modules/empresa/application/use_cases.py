from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.modules.empresa.application.ports import EmpresaDTO, EmpresaRepo
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher
from app.modules.shared.application.base import BaseUseCase


class ListarEmpresasAdmin(BaseUseCase[EmpresaRepo]):
    def execute(self) -> Sequence[EmpresaDTO]:
        return list(self.repo.list_all())


class ListarEmpresasTenant(BaseUseCase[EmpresaRepo]):
    def execute(self, *, tenant_id: uuid.UUID | str) -> Sequence[EmpresaDTO]:
        return list(self.repo.list_by_tenant(tenant_id=tenant_id))


# ----------------------------
# Use-case helper: crear usuario admin de empresa
# ----------------------------
def crear_usuario_admin(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    first_name: str,
    last_name: str,
    email: str,
    username: str,
    password: str,
) -> UsuarioEmpresa:
    """
    Crea un UsuarioEmpresa con rol admin (es_admin_empresa=True),
    validando unicidad de email/username en lower-case. No hace commit.
    Lanza ValueError('user_email_or_username_taken') en caso de colisión.
    """
    email_clean = (email or "").strip().lower()
    username_clean = (username or "").strip().lower()

    exists = (
        db.query(UsuarioEmpresa)
        .filter(
            (func.lower(UsuarioEmpresa.email) == email_clean)
            | (func.lower(UsuarioEmpresa.username) == username_clean)
        )
        .first()
    )
    if exists:
        raise ValueError("user_email_or_username_taken")

    hasher = PasslibPasswordHasher()
    user = UsuarioEmpresa(
        tenant_id=tenant_id,
        first_name=first_name,
        last_name=last_name,
        email=email_clean,
        username=username_clean,
        password_hash=hasher.hash(password),
        is_company_admin=True,
        is_active=True,
    )
    db.add(user)
    return user
