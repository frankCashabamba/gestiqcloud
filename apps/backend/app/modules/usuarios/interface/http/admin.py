from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.security import get_password_hash
from app.models.empresa.usuarioempresa import UsuarioEmpresa


router = APIRouter(
    prefix="/usuarios",  # se monta bajo /api/v1/admin desde build_api_router
    tags=["admin:usuarios"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.post("/{user_id}/set-password")
def set_password(user_id: UUID, payload: SetPasswordIn, db: Session = Depends(get_db)):
    """Establece una contraseÃ±a para un usuario admin (UsuarioEmpresa).

    Requiere scope admin. No devuelve la contraseÃ±a ni el hash.
    """
    user = db.query(UsuarioEmpresa).filter(UsuarioEmpresa.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    # Solo admins de empresa; nunca superusuarios ni otros tipos
    if not bool(getattr(user, "es_admin_empresa", False)):
        raise HTTPException(status_code=403, detail="not_tenant_admin")
    if len(payload.password or "") < 8:
        raise HTTPException(status_code=400, detail="weak_password")

    user.password_hash = get_password_hash(payload.password)
    db.add(user)
    db.commit()
    return {"ok": True}
