from __future__ import annotations

import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.config.database import SessionLocal, get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope

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
        # Ensure table exists when running inline (dev environments may not have applied Alembic yet)
        try:
            db.execute(
                sql_text("""
                    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
                    CREATE TABLE IF NOT EXISTS public.admin_migration_runs (
                      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                      started_at timestamptz NOT NULL DEFAULT now(),
                      finished_at timestamptz,
                      mode text NOT NULL,
                      ok boolean,
                      error text,
                      job_id text,
                      pending_count integer,
                      revisions jsonb,
                      triggered_by text
                    );
                    CREATE INDEX IF NOT EXISTS ix_admin_migration_runs_started ON public.admin_migration_runs (started_at DESC);
                    """)
            )
            try:
                db.commit()
            except Exception:
                pass
        except Exception:
            # Best-effort; if this fails, the insert may still succeed later if Alembic created the table
            try:
                db.rollback()
            except Exception:
                pass
        res = db.execute(
            sql_text("""
                INSERT INTO public.admin_migration_runs (mode, job_id, pending_count, revisions, triggered_by)
                VALUES (:mode, :job_id, :pending_count, COALESCE(:revisions::jsonb, '[]'::jsonb), :triggered_by)
                RETURNING id
                """),
            {
                "mode": mode,
                "job_id": job_id,
                "pending_count": pending_count,
                "revisions": None if not revisions else __import__("json").dumps(revisions),
                "triggered_by": triggered_by,
            },
        )
        row = res.fetchone()
        try:
            db.commit()
        except Exception:
            pass
        return str(row[0]) if row else None
    except Exception:
        return None


def _log_finished(
    db: Session | None, run_id: str | None, ok: bool | None, error: str | None
) -> None:
    try:
        if db is None or not run_id:
            return
        db.execute(
            sql_text("""
                UPDATE public.admin_migration_runs
                SET finished_at = now(), ok = :ok, error = :error
                WHERE id = :id
                """),
            {"id": run_id, "ok": ok, "error": error},
        )
        try:
            db.commit()
        except Exception:
            pass
    except Exception:
        pass


def _run_inline_migrations(db: Session | None = None) -> None:
    """Run Alembic and RLS apply inline in a background task."""
    try:
        migration_state.update(
            {
                "running": True,
                "mode": "inline",
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": None,
                "ok": None,
                "error": None,
            }
        )
        # Compute paths
        backend_dir = Path(__file__).resolve().parents[3]
        root = backend_dir.parent.parent
        env = os.environ.copy()
        # Alembic upgrade head
        subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=str(backend_dir), env=env)
        # Apply RLS defaults/policies (idempotent)
        rls_py = root / "scripts" / "py" / "apply_rls.py"
        if rls_py.exists():
            cmd = ["python", str(rls_py), "--schema", "public", "--set-default"]
            res = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True)
            if res.returncode != 0:
                try:
                    log.error(
                        "inline_migration.rls_failed code=%s stdout=%s stderr=%s",
                        res.returncode,
                        (res.stdout or "").strip(),
                        (res.stderr or "").strip(),
                    )
                except Exception:
                    pass
                # Fallback: try without --set-default (policies only)
                cmd2 = ["python", str(rls_py), "--schema", "public"]
                res2 = subprocess.run(cmd2, cwd=str(root), env=env, capture_output=True, text=True)
                if res2.returncode != 0:
                    try:
                        log.error(
                            "inline_migration.rls_fallback_failed code=%s stdout=%s stderr=%s",
                            res2.returncode,
                            (res2.stdout or "").strip(),
                            (res2.stderr or "").strip(),
                        )
                    except Exception:
                        pass
                    raise subprocess.CalledProcessError(
                        returncode=res2.returncode,
                        cmd=cmd2,
                        output=res2.stdout,
                        stderr=res2.stderr,
                    )
                else:
                    try:
                        log.info("inline_migration.rls_applied_without_default")
                    except Exception:
                        pass
        log.info("Inline migrations completed successfully")
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": True,
                "error": None,
            }
        )
        # finish log using a fresh session (background task context)
        try:
            with SessionLocal() as _s:
                _log_finished(_s, migration_state.get("run_id"), True, None)
        except Exception:
            pass
    except subprocess.CalledProcessError as e:
        log.error("inline_migration_failed: %s", e)
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": False,
                "error": f"inline_migration_failed:{e}",
            }
        )
        try:
            with SessionLocal() as _s:
                _log_finished(
                    _s,
                    migration_state.get("run_id"),
                    False,
                    f"inline_migration_failed:{e}",
                )
        except Exception:
            pass
    except Exception as e:
        log.exception("inline_migration_error: %s", e)
        migration_state.update(
            {
                "running": False,
                "finished_at": datetime.now(UTC).isoformat(),
                "ok": False,
                "error": f"inline_migration_error:{e}",
            }
        )
        try:
            with SessionLocal() as _s:
                _log_finished(
                    _s,
                    migration_state.get("run_id"),
                    False,
                    f"inline_migration_error:{e}",
                )
        except Exception:
            pass


@router.post("/ops/migrate")
def trigger_migrations(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger the Render migrate job if configured.

    Requires env vars:
      - RENDER_API_KEY
      - RENDER_MIGRATE_JOB_ID
    """
    # Prevent concurrent runs
    try:
        if migration_state.get("running"):
            raise HTTPException(status_code=409, detail="migration_in_progress")
    except Exception:
        pass
    # Optional: short-circuit if there are no pending Alembic migrations
    _pending_count = -1
    _pending_revs = []
    try:
        pending, count, revs = _alembic_has_pending()
        _pending_count = count
        _pending_revs = revs or []
        if not pending:
            return {
                "ok": True,
                "mode": "noop",
                "started": False,
                "message": "sin_migraciones_pendientes",
                "pending": False,
                "pending_count": count,
                "pending_revisions": revs or [],
            }
    except Exception:
        # If the check fails, proceed to try migrations to avoid false negatives
        pass

    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    if not job_id or not api_key:
        # Fallback-by-default: run inline Alembic + RLS when Render is not configured
        # Works in DEV/PRO sin coste; ejecuta en background para no bloquear la petición.
        rid = _log_started(db, mode="inline_async")
        migration_state.update({"run_id": rid})
        background_tasks.add_task(_run_inline_migrations)
        return {
            "ok": True,
            "mode": "inline_async",
            "started": True,
            "run_id": rid,
            "configured": False,
            "pending": True,
            "pending_count": _pending_count,
            "pending_revisions": _pending_revs,
        }

    try:
        resp = requests.post(
            f"https://api.render.com/v1/jobs/{job_id}/runs",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={},
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"render_api_unreachable: {e}") from e

    if 200 <= resp.status_code < 300:
        # We cannot track remote job state here; record a hint
        rid = _log_started(db, mode="render_job", job_id=job_id)
        migration_state.update(
            {
                "running": True,
                "mode": "render_job",
                "started_at": datetime.now(UTC).isoformat(),
                "finished_at": None,
                "ok": None,
                "error": None,
                "run_id": rid,
            }
        )
        return {
            "ok": True,
            "mode": "render_job",
            "job_id": job_id,
            "run_id": rid,
            "pending": True,
            "pending_count": _pending_count,
            "pending_revisions": _pending_revs,
        }
    raise HTTPException(status_code=502, detail=f"render_api_error:{resp.status_code}")


@router.get("/ops/migrate/config")
def migrate_config():
    """Report migration execution capabilities for the Admin UI."""
    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    render_configured = bool(job_id and api_key)
    inline_enabled = True  # inline fallback is always available in this build
    return {
        "ok": True,
        "render_configured": render_configured,
        "inline_enabled": inline_enabled,
        "mode": ("render" if render_configured else "inline"),
    }


@router.get("/ops/migrate/status/details")
def migrate_status_details(db: Session = Depends(get_db)):
    """Extended status including last run metadata and config.

    Non-breaking addition to help Admin UI render richer status without
    making multiple calls. Keeps the original /ops/migrate/status intact.
    """
    # Base state
    state = dict(migration_state)

    # Alembic heads (best-effort)
    info = {}
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        backend_dir = Path(__file__).resolve().parents[3]
        cfg = Config(str(backend_dir / "alembic.ini"))
        cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        script = ScriptDirectory.from_config(cfg)
        heads = list(script.get_heads())
        info = {"alembic_heads": {"count": len(heads), "heads": heads}}
    except Exception:
        info = {"alembic_heads": {"count": -1, "heads": []}}

    # Pending Alembic revisions (so UI can decide to disable the button when no changes)
    pending_info = {"pending": True, "pending_count": -1, "pending_revisions": []}
    try:
        p, cnt, revs = _alembic_has_pending()
        pending_info = {
            "pending": bool(p),
            "pending_count": int(cnt),
            "pending_revisions": revs,
        }
    except Exception:
        pass

    # Last run (if table exists)
    last_run = None
    try:
        res = db.execute(
            sql_text("""
                SELECT id::text, started_at, finished_at, mode, ok, error, job_id
                FROM public.admin_migration_runs
                ORDER BY started_at DESC
                LIMIT 1
                """)
        ).first()
        if res:
            last_run = {
                "id": res[0],
                "started_at": res[1].isoformat() if getattr(res[1], "isoformat", None) else res[1],
                "finished_at": res[2].isoformat() if getattr(res[2], "isoformat", None) else res[2],
                "mode": res[3],
                "ok": res[4],
                "error": res[5],
                "job_id": res[6],
            }
    except Exception:
        last_run = None

    render_configured = bool(os.getenv("RENDER_MIGRATE_JOB_ID") and os.getenv("RENDER_API_KEY"))
    inline_enabled = True

    return {
        **state,
        **info,
        **pending_info,
        "config": {
            "render_configured": render_configured,
            "inline_enabled": inline_enabled,
            "mode": ("render" if render_configured else "inline"),
            "last_run": last_run,
            "run_id": migration_state.get("run_id"),
        },
    }


@router.get("/ops/migrate/status")
def migrate_status():
    # Enriquecer con estado Alembic (heads)
    info = {}
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        backend_dir = Path(__file__).resolve().parents[3]
        cfg = Config(str(backend_dir / "alembic.ini"))
        cfg.set_main_option("script_location", str(backend_dir / "alembic"))
        script = ScriptDirectory.from_config(cfg)
        heads = list(script.get_heads())
        info = {"alembic_heads": {"count": len(heads), "heads": heads}}
    except Exception:
        # no romper si Alembic no está disponible en este entorno
        info = {"alembic_heads": {"count": -1, "heads": []}}
    return {**migration_state, **info}


@router.get("/ops/migrate/history")
def migrate_history(limit: int = 20, db: Session = Depends(get_db)):
    try:
        res = db.execute(
            sql_text("""
                SELECT id, started_at, finished_at, mode, ok, error, job_id, pending_count, revisions, triggered_by
                FROM public.admin_migration_runs
                ORDER BY started_at DESC
                LIMIT :limit
                """),
            {"limit": max(1, min(200, int(limit or 20)))},
        )
        rows = [dict(zip(list(res.keys()), r, strict=False)) for r in res.fetchall()]
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
    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    if not job_id or not api_key:
        # Graceful degrade for dev/manual mode: report not configured instead of 501
        return {"ok": True, "configured": False, "status": "not_configured"}
    try:
        resp = requests.get(
            f"https://api.render.com/v1/jobs/{job_id}/runs?limit=1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"render_api_unreachable: {e}") from e

    if not (200 <= resp.status_code < 300):
        raise HTTPException(status_code=502, detail=f"render_api_error:{resp.status_code}")

    try:
        data = resp.json() or {}
    except Exception:
        data = {}

    runs = data if isinstance(data, list) else data.get("data") or data.get("runs") or []
    latest = runs[0] if runs else None
    if not latest:
        return {"ok": True, "updated": False, "status": "unknown"}

    status = str(latest.get("status") or latest.get("state") or "unknown").lower()
    terminal_ok = {"succeeded", "completed", "success"}
    terminal_fail = {"failed", "error", "errored", "canceled", "cancelled"}
    is_terminal = status in terminal_ok or status in terminal_fail
    ok = True if status in terminal_ok else (False if status in terminal_fail else None)

    sel_sql = "SELECT id FROM public.admin_migration_runs WHERE job_id = :job_id AND finished_at IS NULL ORDER BY started_at DESC LIMIT 1"
    row = db.execute(sql_text(sel_sql), {"job_id": job_id}).first()
    if row and is_terminal:
        upd_sql = "UPDATE public.admin_migration_runs SET finished_at = now(), ok = :ok, error = :error WHERE id = :id"
        db.execute(
            sql_text(upd_sql),
            {
                "id": row[0],
                "ok": ok,
                "error": None if ok else f"render_status:{status}",
            },
        )
        try:
            db.commit()
        except Exception:
            pass
        try:
            rid = migration_state.get("run_id")
            if rid and str(rid) == str(row[0]):
                migration_state.update(
                    {
                        "running": False,
                        "finished_at": datetime.now(UTC).isoformat(),
                        "ok": ok,
                        "error": None if ok else f"render_status:{status}",
                    }
                )
        except Exception:
            pass
        return {"ok": True, "updated": True, "status": status}

    return {"ok": True, "updated": False, "status": status}


def _alembic_has_pending() -> tuple[bool, int, list[str]]:
    """Return (pending, count, revisions[]) using Alembic APIs.

    Falls back to considering pending=True on error to be safe.
    """
    try:
        from sqlalchemy import create_engine

        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory
        from app.config.database import make_db_url

        backend_dir = Path(__file__).resolve().parents[3]
        cfg = Config(str(backend_dir / "alembic.ini"))
        cfg.set_main_option("script_location", str(backend_dir / "alembic"))

        engine = create_engine(make_db_url(), future=True)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()

        script = ScriptDirectory.from_config(cfg)
        heads = set(script.get_heads())
        if current in heads:
            return (False, 0, [])

        # Collect revisions between current and heads (best-effort)
        revs: list[str] = []
        for rev in script.walk_revisions(head="heads"):
            # walk_revisions yields from heads backward; stop at current
            if rev.revision == current:
                break
            revs.append(rev.revision)
        revs = list(reversed(revs))
        return (len(revs) > 0, len(revs), revs)
    except Exception:
        return (True, -1, [])
