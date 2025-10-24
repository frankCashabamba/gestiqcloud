
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.usuarios.infrastructure import repositories as repo


def ensure_email_unique(db: Session, email: str, *, exclude_usuario_id: int | None = None) -> None:
    usuario = repo.get_usuario_by_email(db, email)
    if usuario and usuario.id != exclude_usuario_id:
        raise HTTPException(status_code=400, detail="El correo ya está registrado.")


def ensure_username_unique(db: Session, username: str | None, *, exclude_usuario_id: int | None = None) -> None:
    if not username:
        return
    usuario = repo.get_usuario_by_username(db, username)
    if usuario and usuario.id != exclude_usuario_id:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso.")


def validate_modulos_contratados(db: Session, empresa_id: int, modulos: list[int]) -> None:
    if not modulos:
        return
    contratados = set(repo.get_modulos_contratados_ids(db, empresa_id))
    faltantes = [modulo for modulo in modulos if modulo not in contratados]
    if faltantes:
        raise HTTPException(status_code=400, detail=f"Los módulos {faltantes} no están habilitados para la empresa.")


def ensure_not_last_admin(db: Session, empresa_id: int, *, usuario_id: int | None = None) -> None:
    admins = repo.count_admins_empresa(db, empresa_id)
    if admins <= 1 and usuario_id is not None:
        # Si el único admin es el que estamos modificando / desactivando
        existing = repo.get_usuario_by_id(db, usuario_id, empresa_id)
        if existing and existing.es_admin_empresa:
            raise HTTPException(status_code=400, detail="Debe permanecer al menos un administrador activo en la empresa.")
    elif admins == 0:
        raise HTTPException(status_code=400, detail="Debe existir al menos un administrador activo en la empresa.")
