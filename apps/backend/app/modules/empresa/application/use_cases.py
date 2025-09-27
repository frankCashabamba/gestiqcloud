from __future__ import annotations

from typing import Sequence
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.modules.empresa.application.ports import EmpresaRepo, EmpresaDTO
from app.modules.shared.application.base import BaseUseCase
from app.models.empresa.usuarioempresa import UsuarioEmpresa
from app.modules.identity.infrastructure.passwords import PasslibPasswordHasher


class ListarEmpresasAdmin(BaseUseCase[EmpresaRepo]):

    def execute(self) -> Sequence[EmpresaDTO]:
        print("entrooooooooooooooo")    
        return list(self.repo.list_all())


class ListarEmpresasTenant(BaseUseCase[EmpresaRepo]):

    def execute(self, *, tenant_id: int) -> Sequence[EmpresaDTO]:
        return list(self.repo.list_by_tenant(tenant_id=tenant_id))


# ----------------------------
# Use-case helper: crear usuario admin de empresa
# ----------------------------
def crear_usuario_admin(
    db: Session,
    *,
    empresa_id: int,
    nombre_encargado: str,
    apellido_encargado: str,
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
        empresa_id=empresa_id,
        nombre_encargado=nombre_encargado,
        apellido_encargado=apellido_encargado,
        email=email_clean,
        username=username_clean,
        password_hash=hasher.hash(password),
        es_admin_empresa=True,
        activo=True,
    )
    db.add(user)
    return user
