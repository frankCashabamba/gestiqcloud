from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.services.migration_runner import (
    idempotent_migrations_script as _idempotent_migrations_script,
)
from app.services.migration_runner import inline_migrations_allowed as _inline_migrations_allowed
from app.services.migration_runner import repo_root as _repo_root
from app.services.migration_runner import sql_migrations_status as _sql_migrations_status

router = APIRouter(dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))])
log = logging.getLogger("app.admin.ops")

# Simple in-memory status for inline migrations
migration_state = {
    "running": False,
    "mode": None,
    "started_at": None,
    "finished_at": None,
    "ok": None,
    "error": None,
    "run_id": None,
}


def _db_is_postgres(db: Session | None) -> bool:
    try:
        return bool(db and db.bind and db.bind.dialect.name == "postgresql")
    except Exception:
        return False


def _qualified_table_name(db: Session | None, table_name: str) -> str:
    return f"public.{table_name}" if _db_is_postgres(db) else table_name


def _ensure_admin_migration_runs_table(db: Session | None) -> None:
    if db is None:
        return
    table_name = _qualified_table_name(db, "admin_migration_runs")
    db.execute(
        sql_text(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
              id TEXT PRIMARY KEY,
              started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              finished_at TIMESTAMP,
              mode TEXT NOT NULL,
              ok BOOLEAN,
              error TEXT,
              job_id TEXT,
              pending_count INTEGER,
              revisions TEXT,
              triggered_by TEXT
            )
            """
        )
    )
    db.execute(
        sql_text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_admin_migration_runs_started
            ON {table_name} (started_at DESC)
            """
        )
    )
    try:
        db.commit()
    except Exception:
        pass


def _format_subprocess_failure(prefix: str, exc: subprocess.CalledProcessError) -> str:
    details = (exc.stderr or exc.output or "").strip()
    if details:
        details = details[-1500:]
        return f"{prefix}:{details}"
    return f"{prefix}:exit_code={exc.returncode}"


def _normalize_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


@router.get("/ops/schema/missing-id-defaults")
def list_missing_id_defaults(db: Session = Depends(get_db)):
    """List public.* tables whose PK 'id' (integer/bigint) lacks IDENTITY/DEFAULT.
    Helps detect autoincrement issues after resets/migrations.
    """
    try:
        from app.shared.utils import find_missing_id_defaults  # lazy import

        items = find_missing_id_defaults(db)
        return {"ok": True, "count": len(items), "items": items}
    except Exception as e:
        try:
            log.exception("missing_id_defaults_list_failed: %s", e)
        except Exception as e:
            pass
        raise HTTPException(status_code=500, detail=f"schema_check_error:{e}") from e


def _log_started(
    db: Session | None,
    mode: str,
    job_id: str | None = None,
    pending_count: int | None = None,
    revisions: list[str] | None = None,
    triggered_by: str | None = None,
) -> str | None:
    """Insert a row into admin_migration_runs and return run id (or None)."""
    try:
        if db is None:
            return None
        _ensure_admin_migration_runs_table(db)
        run_id = str(uuid4())
        table_name = _qualified_table_name(db, "admin_migration_runs")
        db.execute(
            sql_text(
                f"""
                INSERT INTO {table_name} (id, mode, job_id, pending_count, revisions, triggered_by)
                VALUES (:id, :mode, :job_id, :pending_count, :revisions, :triggered_by)
                """
            ),
            {
                "id": run_id,
                "mode": mode,
                "job_id": job_id,
                "pending_count": pending_count,
                "revisions": json.dumps(revisions or []),
                "triggered_by": triggered_by,
            },
        )
        try:
            db.commit()
        except Exception:
            pass
        return run_id
    except Exception:
        return None


def _log_finished(
    db: Session | None, run_id: str | None, ok: bool | None, error: str | None
) -> None:
    try:
        if db is None or not run_id:
            return
        table_name = _qualified_table_name(db, "admin_migration_runs")
        db.execute(
            sql_text(
                f"""
                UPDATE {table_name}
                SET finished_at = :finished_at, ok = :ok, error = :error
                WHERE id = :id
                """
            ),
            {
                "id": run_id,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": ok,
                "error": error,
            },
        )
        try:
            db.commit()
        except Exception:
            pass
    except Exception:
        pass


def _run_sql_idempotent_migrations(run_id: str | None = None) -> None:
    """Run the tracked SQL migration script in a background task."""
    try:
        if not _inline_migrations_allowed():
            raise RuntimeError("inline_migrations_disabled")
        root = _repo_root()
        script_path = _idempotent_migrations_script()
        if not script_path.exists():
            raise FileNotFoundError(f"migration_script_missing:{script_path}")

        env = os.environ.copy()
        if env.get("DB_DSN") and not env.get("DATABASE_URL"):
            env["DATABASE_URL"] = env["DB_DSN"]
        cmd = [sys.executable or "python", str(script_path)]
        res = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True)
        if res.returncode != 0:
            raise subprocess.CalledProcessError(
                returncode=res.returncode,
                cmd=cmd,
                output=res.stdout,
                stderr=res.stderr,
            )

        log.info(
            "sql_idempotent_migrations_completed stdout=%s", (res.stdout or "").strip()[-1000:]
        )
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": True,
                "error": None,
            }
        )
        try:
            with SessionLocal() as _s:
                _log_finished(_s, run_id or migration_state.get("run_id"), True, None)
        except Exception:
            pass
    except subprocess.CalledProcessError as e:
        error = _format_subprocess_failure("sql_idempotent_migration_failed", e)
        log.error("%s", error)
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": False,
                "error": error,
            }
        )
        try:
            with SessionLocal() as _s:
                _log_finished(
                    _s,
                    run_id or migration_state.get("run_id"),
                    False,
                    error,
                )
        except Exception:
            pass
    except Exception as e:
        log.exception("sql_idempotent_migration_error: %s", e)
        error = f"sql_idempotent_migration_error:{e}"
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": False,
                "error": error,
            }
        )
        try:
            with SessionLocal() as _s:
                _log_finished(
                    _s,
                    run_id or migration_state.get("run_id"),
                    False,
                    error,
                )
        except Exception:
            pass


@router.post("/ops/migrate")
def trigger_migrations(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger tracked SQL migrations via the idempotent ops script."""
    # Prevent concurrent runs
    try:
        if migration_state.get("running"):
            raise HTTPException(status_code=409, detail="migration_in_progress")
    except Exception:
        pass
    if not _inline_migrations_allowed():
        raise HTTPException(status_code=503, detail="inline_migrations_disabled")
    script_path = _idempotent_migrations_script()
    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"migration_script_missing:{script_path}")

    # Short-circuit if there are no pending tracked SQL migrations
    _pending_count = -1
    _pending_revs = []
    _applied_count = 0
    try:
        pending, count, revs, applied_count = _sql_migrations_status(db)
        _pending_count = count
        _pending_revs = revs or []
        _applied_count = applied_count
        if not pending:
            return {
                "ok": True,
                "mode": "noop",
                "started": False,
                "message": "sin_migraciones_pendientes",
                "pending": False,
                "pending_count": count,
                "pending_revisions": revs or [],
                "applied_count": applied_count,
            }
    except Exception:
        # If the check fails, proceed to try migrations to avoid false negatives
        pass

    run_id = _log_started(
        db,
        mode="sql_idempotent_async",
        pending_count=_pending_count,
        revisions=_pending_revs,
    )
    migration_state.update(
        {
            "running": True,
            "mode": "sql_idempotent_async",
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": None,
            "ok": None,
            "error": None,
            "run_id": run_id,
        }
    )
    background_tasks.add_task(_run_sql_idempotent_migrations, run_id)
    return {
        "ok": True,
        "mode": "sql_idempotent_async",
        "started": True,
        "run_id": run_id,
        "configured": True,
        "runner": str(script_path.relative_to(_repo_root())).replace("\\", "/"),
        "pending": True,
        "pending_count": _pending_count,
        "pending_revisions": _pending_revs,
        "applied_count": _applied_count,
    }


@router.get("/ops/migrate/config")
def migrate_config():
    """Report migration execution capabilities for the Admin UI."""
    allow_inline = _inline_migrations_allowed()
    script_path = _idempotent_migrations_script()
    inline_enabled = allow_inline and script_path.exists()
    reason = None
    if not allow_inline:
        reason = "inline_migrations_disabled"
    elif not script_path.exists():
        reason = f"migration_script_missing:{script_path}"
    return {
        "ok": True,
        "render_configured": False,
        "allow_inline": allow_inline,
        "inline_enabled": inline_enabled,
        "mode": ("sql_idempotent" if inline_enabled else "unavailable"),
        "runner": "ops/scripts/migrate_all_migrations_idempotent.py",
        "reason": reason,
    }


@router.get("/ops/migrate/status/details")
def migrate_status_details(db: Session = Depends(get_db)):
    """Extended status including last run metadata and config.

    Non-breaking addition to help Admin UI render richer status without
    making multiple calls. Keeps the original /ops/migrate/status intact.
    """
    # Base state
    state = dict(migration_state)

    # Pending tracked SQL migrations
    pending_info = {
        "pending": True,
        "pending_count": -1,
        "pending_revisions": [],
        "applied_count": 0,
    }
    try:
        p, cnt, revs, applied_count = _sql_migrations_status(db)
        pending_info = {
            "pending": bool(p),
            "pending_count": int(cnt),
            "pending_revisions": revs,
            "applied_count": int(applied_count),
        }
    except Exception:
        pass

    # Last run (if table exists)
    last_run = None
    try:
        table_name = _qualified_table_name(db, "admin_migration_runs")
        res = db.execute(
            sql_text(
                f"""
                SELECT id, started_at, finished_at, mode, ok, error, job_id
                FROM {table_name}
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        ).first()
        if res:
            last_run = {
                "id": res[0],
                "started_at": res[1].isoformat() if getattr(res[1], "isoformat", None) else res[1],
                "finished_at": res[2].isoformat() if getattr(res[2], "isoformat", None) else res[2],
                "mode": res[3],
                "ok": _normalize_bool(res[4]),
                "error": res[5],
                "job_id": res[6],
            }
    except Exception:
        last_run = None

    allow_inline = _inline_migrations_allowed()
    script_path = _idempotent_migrations_script()
    inline_enabled = allow_inline and script_path.exists()
    reason = None
    if not allow_inline:
        reason = "inline_migrations_disabled"
    elif not script_path.exists():
        reason = f"migration_script_missing:{script_path}"

    return {
        **state,
        **pending_info,
        "config": {
            "render_configured": False,
            "allow_inline": allow_inline,
            "inline_enabled": inline_enabled,
            "mode": ("sql_idempotent" if inline_enabled else "unavailable"),
            "runner": "ops/scripts/migrate_all_migrations_idempotent.py",
            "reason": reason,
            "last_run": last_run,
            "run_id": migration_state.get("run_id"),
        },
    }


@router.get("/ops/migrate/status")
def migrate_status(db: Session = Depends(get_db)):
    state = dict(migration_state)
    if not state.get("running"):
        try:
            table_name = _qualified_table_name(db, "admin_migration_runs")
            row = db.execute(
                sql_text(
                    f"""
                    SELECT id, started_at, finished_at, mode, ok, error
                    FROM {table_name}
                    ORDER BY started_at DESC
                    LIMIT 1
                    """
                )
            ).first()
            if row:
                state.update(
                    {
                        "run_id": row[0],
                        "started_at": (
                            row[1].isoformat() if getattr(row[1], "isoformat", None) else row[1]
                        ),
                        "finished_at": (
                            row[2].isoformat() if getattr(row[2], "isoformat", None) else row[2]
                        ),
                        "mode": row[3],
                        "ok": _normalize_bool(row[4]),
                        "error": row[5],
                    }
                )
        except Exception:
            pass
    return state


@router.get("/ops/migrate/history")
def migrate_history(limit: int = 20, db: Session = Depends(get_db)):
    try:
        table_name = _qualified_table_name(db, "admin_migration_runs")
        res = db.execute(
            sql_text(
                f"""
                SELECT id, started_at, finished_at, mode, ok, error, job_id, pending_count, revisions, triggered_by
                FROM {table_name}
                ORDER BY started_at DESC
                LIMIT :limit
                """
            ),
            {"limit": max(1, min(200, int(limit or 20)))},
        )
        rows = [dict(zip(list(res.keys()), r, strict=False)) for r in res.fetchall()]
        for row in rows:
            row["ok"] = _normalize_bool(row.get("ok"))
            revisions = row.get("revisions")
            if isinstance(revisions, str):
                try:
                    row["revisions"] = json.loads(revisions)
                except Exception:
                    pass
        return {"ok": True, "items": rows}
    except Exception as e:
        # If table doesn't exist yet, return empty history instead of 500
        msg = str(e).lower()
        if "admin_migration_runs" in msg and (
            "does not exist" in msg or "no existe" in msg or "undefined" in msg
        ):
            return {"ok": True, "items": []}
        raise HTTPException(status_code=500, detail=f"history_error:{e}") from e


@router.post("/ops/migrate/refresh")
def migrate_refresh(db: Session = Depends(get_db)):
    if migration_state.get("running"):
        return {"ok": True, "updated": False, "status": "running"}
    try:
        table_name = _qualified_table_name(db, "admin_migration_runs")
        row = db.execute(
            sql_text(
                f"""
                SELECT ok
                FROM {table_name}
                ORDER BY started_at DESC
                LIMIT 1
                """
            )
        ).first()
        if not row:
            return {"ok": True, "updated": False, "status": "idle"}
        last_ok = _normalize_bool(row[0])
        if last_ok is True:
            return {"ok": True, "updated": False, "status": "success"}
        if last_ok is False:
            return {"ok": True, "updated": False, "status": "failed"}
    except Exception:
        pass
    return {"ok": True, "updated": False, "status": "idle"}
