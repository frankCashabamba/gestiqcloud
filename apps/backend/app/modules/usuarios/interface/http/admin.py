from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.core.security import get_password_hash
from app.models.auth.useradmis import SuperUser


router = APIRouter(
    prefix="/usuarios",  # se monta bajo /api/v1/admin desde build_api_router
    tags=["admin:usuarios"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=8)


@router.post("/{user_id}/set-password")
def set_password(user_id: int, payload: SetPasswordIn, db: Session = Depends(get_db)):
    """Establece una contraseña para un usuario admin (SuperUser).

    Requiere scope admin. No devuelve la contraseña ni el hash.
    """
    user = db.get(SuperUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user_not_found")
    if len(payload.password or "") < 8:
        raise HTTPException(status_code=400, detail="weak_password")

    user.password_hash = get_password_hash(payload.password)
    db.add(user)
    db.commit()
    return {"ok": True}
