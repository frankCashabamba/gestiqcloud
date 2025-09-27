
from fastapi import Depends, HTTPException

from app.routers.protected import get_current_user
from app.schemas.configuracion import AuthenticatedUser


def require_empresa_admin(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
    if current_user.is_superadmin or getattr(current_user, "es_admin_empresa", False):
        return current_user
    raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador de empresa.")


def ensure_empresa_scope(user: AuthenticatedUser, empresa_id: int) -> None:
    if user.is_superadmin:
        return
    if user.empresa_id != empresa_id:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta empresa.")
