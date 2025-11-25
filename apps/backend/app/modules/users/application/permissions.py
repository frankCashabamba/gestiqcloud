from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.company.company_role import CompanyRole
from app.models.company.company_user_role import CompanyUserRole
from app.routers.protected import get_current_user
from app.schemas.configuracion import AuthenticatedUser


def require_company_admin(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current_user.is_superadmin or getattr(current_user, "is_company_admin", False):
        return current_user
    raise HTTPException(status_code=403, detail="Company admin privileges required.")


def ensure_company_scope(user: AuthenticatedUser, tenant_id: int) -> None:
    if user.is_superadmin:
        return
    if user.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="No access to this company.")


# ---- Permisos granulares (v1):
# For now, delegate to company admin while granular perms are stabilized.


def _flatten_perms(perms: dict) -> set[str]:
    out: set[str] = set()
    for k, v in (perms or {}).items():
        if isinstance(v, dict):
            for act, allowed in v.items():
                if allowed:
                    out.add(f"{k}:{act}")
        else:
            if v:
                out.add(str(k))
    return out


def _has_perm(db: Session, user: AuthenticatedUser, perm_key: str) -> bool:
    # Superadmin or company admin: full access
    if getattr(user, "is_superadmin", False) or getattr(user, "is_company_admin", False):
        return True
    tenant_id = getattr(user, "tenant_id", None)
    user_id = getattr(user, "user_id", None)
    if not tenant_id or not user_id:
        return False
    role_ids = [
        rid
        for (rid,) in (
            db.query(CompanyUserRole.rol_id)
            .filter(
                CompanyUserRole.tenant_id == tenant_id,
                CompanyUserRole.usuario_id == int(user_id),
                CompanyUserRole.activo.is_(True),
            )
            .all()
        )
    ]
    if not role_ids:
        return False
    rows = (
        db.query(CompanyRole.permissions)
        .filter(CompanyRole.id.in_(role_ids), CompanyRole.tenant_id == tenant_id)
        .all()
    )
    acc: set[str] = set()
    for (perm_dict,) in rows:
        if isinstance(perm_dict, dict):
            acc |= _flatten_perms(perm_dict)
    return perm_key in acc


def _require_perm(perm_key: str, db: Session, current_user: AuthenticatedUser) -> AuthenticatedUser:
    if _has_perm(db, current_user, perm_key):
        return current_user
    raise HTTPException(status_code=403, detail="forbidden")


def require_perm_create_tenant_user(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return _require_perm("usuarios:create", db, current_user)


def require_perm_update_tenant_user(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return _require_perm("usuarios:update", db, current_user)


def require_perm_delete_tenant_user(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return _require_perm("usuarios:delete", db, current_user)


def require_perm_set_password_tenant_user(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return _require_perm("usuarios:set_password", db, current_user)
