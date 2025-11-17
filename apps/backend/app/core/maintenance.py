# app/core/maintenance.py
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.auth.refresh_family import RefreshToken, RefreshTokenFamily  # ajusta


def gc_refresh_tokens(db: Session, older_than_days: int = 60) -> int:
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    # 1) borrar tokens expirados/used con exp < now - margen
    # 2) borrar familias sin tokens activos
    # Pseudocódigo – ajusta SQLAlchemy a tu esquema
    n = 0
    n += (
        db.query(RefreshToken)
        .filter(RefreshToken.expires_at < cutoff)
        .delete(synchronize_session=False)
    )
    n += (
        db.query(RefreshTokenFamily)
        .filter(~RefreshTokenFamily.tokens.any())
        .delete(synchronize_session=False)
    )
    db.commit()
    return n
