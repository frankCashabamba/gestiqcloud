"""Identity: /me endpoint for current user info."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.core.user import User

router = APIRouter(tags=["Identity"])


class MeResponse(BaseModel):
    id: str
    email: str
    name: str | None = None
    is_active: bool
    tenant_id: str | None = None


@router.get("/me", response_model=MeResponse)
def me(request: Request, db: Session = Depends(get_db)):
    """Return current authenticated user info."""
    claims = getattr(request.state, "access_claims", {})
    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    from uuid import UUID

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return MeResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        tenant_id=claims.get("tenant_id"),
    )
