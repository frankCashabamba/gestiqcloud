# app/api/v1/me/sessions.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.core.authz import require_scope
from app.core.access_guard import with_access_claims
from app.db.rls import ensure_rls
from app.models.auth.refresh_family import RefreshFamily  # ajusta a tu modelo real

router = APIRouter(
    prefix="/me",
    tags=["Me"],
    dependencies=[Depends(with_access_claims), Depends(ensure_rls)],
)


@router.get("/sessions", dependencies=[Depends(require_scope("tenant"))])
def list_sessions(request: Request, db: Session = Depends(get_db)):
    user_id = request.state.access_claims["user_id"]
    rows = (
        db.query(RefreshFamily)
        .filter(RefreshFamily.user_id == user_id, RefreshFamily.revoked == False)  # noqa
        .order_by(RefreshFamily.created_at.desc())
        .limit(50)
        .all()
    )
    # serializa lo mínimo (UA, IP, created_at, last_used_at si lo guardas)
    return [
        {"id": r.id, "ua": r.user_agent, "ip": r.ip, "created_at": r.created_at}
        for r in rows
    ]
