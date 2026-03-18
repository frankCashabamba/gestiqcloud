"""Router for schema migrations management."""

import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.services.migration_runner import (
    list_sql_migration_names,
    load_applied_sql_migration_names,
    migration_friendly_name,
)

router = APIRouter(
    prefix="/migrations",
    tags=["migrations"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _schema_migrations_ddl(db: Session) -> str:
    if db.bind and db.bind.dialect.name == "postgresql":
        return """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id            SERIAL PRIMARY KEY,
                version       VARCHAR NOT NULL UNIQUE,
                name          VARCHAR,
                status        VARCHAR NOT NULL DEFAULT 'pending',
                mode          VARCHAR,
                started_at    TIMESTAMPTZ,
                completed_at  TIMESTAMPTZ,
                executed_by   VARCHAR,
                execution_time_ms INTEGER,
                error_message TEXT,
                applied_order INTEGER,
                created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    return """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            version       VARCHAR NOT NULL UNIQUE,
            name          VARCHAR,
            status        VARCHAR NOT NULL DEFAULT 'pending',
            mode          VARCHAR,
            started_at    TIMESTAMP,
            completed_at  TIMESTAMP,
            executed_by   VARCHAR,
            execution_time_ms INTEGER,
            error_message TEXT,
            applied_order INTEGER,
            created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """


def _ensure_schema_migrations_table(db: Session) -> None:
    """Crea schema_migrations si no existe y la siembra desde _migrations."""
    try:
        db.execute(text(_schema_migrations_ddl(db)))
        # Sembrar desde _migrations (runner idempotente) si la tabla existe,
        applied_versions = load_applied_sql_migration_names(db)
        known_versions = set(list_sql_migration_names()) | applied_versions
        for version in sorted(known_versions):
            status_value = "success" if version in applied_versions else "pending"
            db.execute(
                text(
                    """
                    INSERT INTO schema_migrations (
                        version, name, status, completed_at, created_at, updated_at
                    )
                    VALUES (
                        :version,
                        :name,
                        :status,
                        :completed_at,
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT (version) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = CASE
                            WHEN EXCLUDED.status = 'success' THEN 'success'
                            WHEN schema_migrations.status IN ('running', 'failed', 'ignored')
                                THEN schema_migrations.status
                            ELSE EXCLUDED.status
                        END,
                        completed_at = CASE
                            WHEN EXCLUDED.status = 'success'
                                THEN COALESCE(schema_migrations.completed_at, EXCLUDED.completed_at)
                            ELSE schema_migrations.completed_at
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    """
                ),
                {
                    "version": version,
                    "name": migration_friendly_name(version),
                    "status": status_value,
                    "completed_at": datetime.now(UTC) if status_value == "success" else None,
                },
            )
        db.commit()
    except Exception:
        db.rollback()


class MigrationRecord(BaseModel):
    """Migration record."""

    id: int
    version: str
    name: str | None = None
    status: str
    mode: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    executed_by: str | None = None
    execution_time_ms: int | None = None
    error_message: str | None = None
    applied_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class MigrationExecuteResponse(BaseModel):
    """Migration execution response."""

    ok: bool
    message: str
    job_id: str | None = None
    migrations_applied: int = 0


@router.get("/history", response_model=list[MigrationRecord])
async def get_migration_history(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Get executed migrations history.
    Only accessible to administrators.
    """
    _ensure_schema_migrations_table(db)
    result = (
        db.execute(
            text(
                """
            SELECT
                id, version, name, status, mode,
                started_at, completed_at, executed_by,
                execution_time_ms, error_message, applied_order,
                created_at, updated_at
            FROM schema_migrations
            ORDER BY applied_order DESC NULLS LAST, created_at DESC
            LIMIT :limit
        """
            ),
            {"limit": limit},
        )
        .mappings()
        .all()
    )

    return [MigrationRecord(**dict(row)) for row in result]


@router.get("/status")
async def get_migration_status(
    db: Session = Depends(get_db),
):
    """
    Get current migration system status.
    """
    _ensure_schema_migrations_table(db)
    stats = (
        db.execute(
            text(
                """
            SELECT
                status,
                COUNT(*) as count
            FROM schema_migrations
            GROUP BY status
        """
            )
        )
        .mappings()
        .all()
    )

    last_migration = (
        db.execute(
            text(
                """
                SELECT version, name, completed_at, status
                FROM schema_migrations
                WHERE status = 'success'
                ORDER BY
                    applied_order DESC NULLS LAST,
                    COALESCE(completed_at, updated_at, created_at) DESC NULLS LAST
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )

    pending_count = db.execute(
        text("SELECT COUNT(*) FROM schema_migrations WHERE status = 'pending'")
    ).scalar()

    return {
        "stats": {row["status"]: row["count"] for row in stats},
        "last_migration": dict(last_migration) if last_migration else None,
        "pending_count": pending_count,
        "mode": "manual",
    }


@router.post("/execute", response_model=MigrationExecuteResponse)
async def execute_migrations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Trigger the same idempotent SQL runner used by the admin ops button.
    """
    from app.routers.admin import ops as admin_ops

    payload = admin_ops.trigger_migrations(background_tasks=background_tasks, db=db)
    return MigrationExecuteResponse(
        ok=bool(payload.get("ok")),
        message=(
            "Migrations in progress (idempotent runner)"
            if payload.get("started")
            else str(payload.get("message") or "sin_migraciones_pendientes")
        ),
        job_id=payload.get("run_id") or payload.get("job_id"),
        migrations_applied=0,
    )


@router.get("/pending")
async def get_pending_migrations(
    db: Session = Depends(get_db),
):
    """Get pending migrations."""
    _ensure_schema_migrations_table(db)
    result = (
        db.execute(
            text(
                """
            SELECT version, name, created_at
            FROM schema_migrations
            WHERE status = 'pending'
            ORDER BY version
        """
            )
        )
        .mappings()
        .all()
    )

    return [dict(row) for row in result]


class MigrationMarkRequest(BaseModel):
    """Request to mark migration status."""

    version: str
    status: str  # 'pending'|'running'|'success'|'failed'|'ignored'
    note: str | None = None


class MigrationMarkResponse(BaseModel):
    ok: bool
    version: str
    status: str
    message: str


@router.post("/mark", response_model=MigrationMarkResponse)
async def mark_migration_status(
    body: MigrationMarkRequest,
    db: Session = Depends(get_db),
):
    """Mark migration status in schema_migrations.

    Useful to ignore ('ignored') a problematic migration or revert to 'pending'.
    """
    _ensure_schema_migrations_table(db)
    allowed = {"pending", "running", "success", "failed", "ignored"}
    st = body.status.lower().strip()
    if st not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    version = body.version
    try:
        mig_root = os.getenv("MIGRATIONS_DIR", "ops/migrations")
        d = Path(mig_root) / version
        friendly = migration_friendly_name(d if d.exists() else version)
    except Exception:
        friendly = version

    try:
        db.execute(
            text(
                """
                INSERT INTO schema_migrations(version, name, status, started_at, completed_at, updated_at, error_message)
                VALUES (:v, :n, :s, CASE WHEN :s = 'running' THEN NOW() END, CASE WHEN :s = 'success' THEN NOW() END, NOW(), :note)
                ON CONFLICT (version) DO UPDATE SET
                    name = EXCLUDED.name,
                    status = EXCLUDED.status,
                    updated_at = NOW(),
                    completed_at = CASE WHEN EXCLUDED.status = 'success' THEN NOW() ELSE schema_migrations.completed_at END,
                    started_at = CASE WHEN EXCLUDED.status = 'running' THEN NOW() ELSE schema_migrations.started_at END,
                    error_message = COALESCE(EXCLUDED.error_message, schema_migrations.error_message)
                """
            ),
            {"v": version, "n": friendly, "s": st, "note": (body.note or None)},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Could not mark migration: {e}")

    return MigrationMarkResponse(ok=True, version=version, status=st, message="Status updated")
