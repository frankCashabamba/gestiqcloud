from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.identity.application.ports import RefreshTokenRepo
from app.core.refresh import _utcnow as _utcnow  # reuse proven helper
from app.core.refresh import _hash as _hash


class SqlRefreshTokenRepo(RefreshTokenRepo):
    def __init__(self, db: Session):
        self.db = db

    def create_family(self, *, user_id: str, tenant_id: str | None) -> str:
        from uuid import uuid4

        family_id = str(uuid4())
        self.db.execute(
            text(
                """
                INSERT INTO auth_refresh_family (id, user_id, tenant_id, created_at, revoked_at)
                VALUES (:id, :user_id, :tenant_id, :created_at, NULL)
                """
            ),
            {"id": family_id, "user_id": user_id, "tenant_id": tenant_id, "created_at": _utcnow()},
        )
        self.db.commit()
        return family_id

    def issue_token(
        self,
        *,
        family_id: str,
        prev_jti: str | None,
        user_agent: str,
        ip: str,
    ) -> str:
        from uuid import uuid4

        jti = str(uuid4())
        self.db.execute(
            text(
                """
                INSERT INTO auth_refresh_token
                  (id, family_id, jti, prev_jti, used_at, revoked_at, ua_hash, ip_hash, created_at)
                VALUES
                  (:id, :family_id, :jti, :prev_jti, NULL, NULL, :ua_hash, :ip_hash, :created_at)
                """
            ),
            {
                "id": str(uuid4()),
                "family_id": family_id,
                "jti": jti,
                "prev_jti": prev_jti,
                "ua_hash": _hash(user_agent or ""),
                "ip_hash": _hash(ip or ""),
                "created_at": _utcnow(),
            },
        )
        self.db.commit()
        return jti

    def mark_used(self, *, jti: str) -> None:
        self.db.execute(
            text(
                """
                UPDATE auth_refresh_token
                   SET used_at = :ts
                 WHERE jti = :jti
                """
            ),
            {"jti": jti, "ts": _utcnow()},
        )
        self.db.commit()

    def is_reused_or_revoked(self, *, jti: str) -> bool:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT used_at, revoked_at
                      FROM auth_refresh_token
                     WHERE jti = :jti
                     LIMIT 1
                    """
                ),
                {"jti": jti},
            )
            .mappings()
            .first()
        )
        if row is None:
            return True
        return (row["used_at"] is not None) or (row["revoked_at"] is not None)

    def revoke_family(self, *, family_id: str) -> None:
        now = _utcnow()
        self.db.execute(
            text(
                """
                UPDATE auth_refresh_family
                   SET revoked_at = :ts
                 WHERE id = :fid
                """
            ),
            {"fid": family_id, "ts": now},
        )
        self.db.execute(
            text(
                """
                UPDATE auth_refresh_token
                   SET revoked_at = :ts
                 WHERE family_id = :fid
                """
            ),
            {"fid": family_id, "ts": now},
        )
        self.db.commit()

    def get_family(self, *, jti: str) -> Optional[str]:
        row = (
            self.db.execute(
                text(
                    """
                    SELECT family_id
                      FROM auth_refresh_token
                     WHERE jti = :jti
                     LIMIT 1
                    """
                ),
                {"jti": jti},
            )
            .mappings()
            .first()
        )
        return str(row["family_id"]) if row else None

