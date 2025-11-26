from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.users.infrastructure import repositories as repo


def ensure_email_unique(db: Session, email: str, *, exclude_user_id: int | None = None) -> None:
    usuario = repo.get_user_by_email(db, email)
    if usuario and usuario.id != exclude_user_id:
        raise HTTPException(status_code=400, detail="Email already registered.")


def ensure_username_unique(
    db: Session, username: str | None, *, exclude_user_id: int | None = None
) -> None:
    if not username:
        return
    usuario = repo.get_user_by_username(db, username)
    if usuario and usuario.id != exclude_user_id:
        raise HTTPException(status_code=400, detail="Username already in use.")


def validate_contracted_modules(db: Session, tenant_id: int, modules: list[int]) -> None:
    if not modules:
        return
    contracted = set(repo.get_contracted_module_ids(db, tenant_id))
    missing = [module for module in modules if module not in contracted]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Modules {missing} are not enabled for this company.",
        )


def ensure_not_last_admin(db: Session, tenant_id: int, *, user_id: int | None = None) -> None:
    admins = repo.count_company_admins(db, tenant_id)
    if admins <= 1 and user_id is not None:
        # Si el único admin es el que estamos modificando / desactivando
        existing = repo.get_user_by_id(db, user_id, tenant_id)
        if existing and existing.is_company_admin:
            raise HTTPException(
                status_code=400,
                detail="At least one active company admin is required.",
            )
    elif admins == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one active company admin must exist.",
        )
