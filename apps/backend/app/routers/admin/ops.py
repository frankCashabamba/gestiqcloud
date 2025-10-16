from __future__ import annotations

import os
import requests
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session
from app.config.database import get_db, SessionLocal
from pathlib import Path
import subprocess
from app.core.authz import require_scope
import logging
from datetime import datetime, timezone
from app.core.access_guard import with_access_claims

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


def _log_started(db: Session | None, mode: str, job_id: str | None = None,
                 pending_count: int | None = None, revisions: list[str] | None = None,
                 triggered_by: str | None = None) -> str | None:
    """Insert a row into admin_migration_runs and return run id (or None)."""
    try:
        if db is None:
            return None
        res = db.execute(
            sql_text(
                """
                INSERT INTO public.admin_migration_runs (mode, job_id, pending_count, revisions, triggered_by)
                VALUES (:mode, :job_id, :pending_count, COALESCE(:revisions::jsonb, '[]'::jsonb), :triggered_by)
                RETURNING id
                """
            ),
            {
                "mode": mode,
                "job_id": job_id,
                "pending_count": pending_count,
                "revisions": None if not revisions else __import__('json').dumps(revisions),
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


def _log_finished(db: Session | None, run_id: str | None, ok: bool | None, error: str | None) -> None:
    try:
        if db is None or not run_id:
            return
        db.execute(
            sql_text(
                """
                UPDATE public.admin_migration_runs
                SET finished_at = now(), ok = :ok, error = :error
                WHERE id = :id
                """
            ),
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
        migration_state.update({
            "running": True,
            "mode": "inline",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "ok": None,
            "error": None,
        })
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
                    raise subprocess.CalledProcessError(returncode=res2.returncode, cmd=cmd2, output=res2.stdout, stderr=res2.stderr)
                else:
                    try:
                        log.info("inline_migration.rls_applied_without_default")
                    except Exception:
                        pass
        log.info("Inline migrations completed successfully")
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": True,
            "error": None,
        })
        # finish log using a fresh session (background task context)
        try:
            with SessionLocal() as _s:
                _log_finished(_s, migration_state.get("run_id"), True, None)
        except Exception:
            pass
    except subprocess.CalledProcessError as e:
        log.error("inline_migration_failed: %s", e)
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": f"inline_migration_failed:{e}",
        })
        try:
            with SessionLocal() as _s:
                _log_finished(_s, migration_state.get("run_id"), False, f"inline_migration_failed:{e}")
        except Exception:
            pass
    except Exception as e:
        log.exception("inline_migration_error: %s", e)
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": f"inline_migration_error:{e}",
        })
        try:
            with SessionLocal() as _s:
                _log_finished(_s, migration_state.get("run_id"), False, f"inline_migration_error:{e}")
        except Exception:
            pass


@router.post("/ops/migrate")
def trigger_migrations(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Prevent concurrent runs
    try:
        if migration_state.get("running"):
            raise HTTPException(status_code=409, detail="migration_in_progress")
    except Exception:
        pass
    # Optional: short-circuit if there are no pending Alembic migrations
    try:
        pending, count, _ = _alembic_has_pending()
        if not pending:
            return {"ok": True, "mode": "noop", "started": False, "message": "sin_migraciones_pendientes", "pending_count": count}
    except Exception:
        # If the check fails, proceed to try migrations to avoid false negatives
        pass
    """Trigger the Render migrate job if configured.

    Requires env vars:
      - RENDER_API_KEY
      - RENDER_MIGRATE_JOB_ID
    """
    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    if not job_id or not api_key:
        # Optional fallback: run inline Alembic + RLS if explicitly allowed
        if str(os.getenv("ALLOW_INLINE_MIGRATIONS", "0")).lower() in ("1", "true", "yes"):
            # Run asynchronously to avoid request timeouts (CF/Render ~100s)
            rid = _log_started(db, mode="inline_async")
            migration_state.update({"run_id": rid})
            background_tasks.add_task(_run_inline_migrations)
            return {"ok": True, "mode": "inline_async", "started": True, "run_id": rid}
        raise HTTPException(status_code=501, detail="render_job_not_configured")

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
        migration_state.update({
            "running": True,
            "mode": "render_job",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "ok": None,
            "error": None,
            "run_id": rid,
        })
        return {"ok": True, "job_id": job_id, "run_id": rid}
    raise HTTPException(status_code=502, detail=f"render_api_error:{resp.status_code}")


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
            sql_text(
                """
                SELECT id, started_at, finished_at, mode, ok, error, job_id, pending_count, revisions, triggered_by
                FROM public.admin_migration_runs
                ORDER BY started_at DESC
                LIMIT :limit
                """
            ),
            {"limit": max(1, min(200, int(limit or 20)))},
        )
        rows = [dict(zip([c for c in res.keys()], r)) for r in res.fetchall()]
        return {"ok": True, "items": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"history_error:{e}")


@router.post("/ops/migrate/refresh")
def migrate_refresh(db: Session = Depends(get_db)):
    job_id = os.getenv("RENDER_MIGRATE_JOB_ID")
    api_key = os.getenv("RENDER_API_KEY")
    if not job_id or not api_key:
        raise HTTPException(status_code=501, detail="render_job_not_configured")
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
        db.execute(sql_text(upd_sql), {"id": row[0], "ok": ok, "error": None if ok else f"render_status:{status}"})
        try:
            db.commit()
        except Exception:
            pass
        try:
            rid = migration_state.get("run_id")
            if rid and str(rid) == str(row[0]):
                migration_state.update({
                    "running": False,
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "ok": ok,
                    "error": None if ok else f"render_status:{status}",
                })
        except Exception:
            pass
        return {"ok": True, "updated": True, "status": status}

    return {"ok": True, "updated": False, "status": status}


def _alembic_has_pending() -> tuple[bool, int, list[str]]:
    """Return (pending, count, revisions[]) using Alembic APIs.

    Falls back to considering pending=True on error to be safe.
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
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
