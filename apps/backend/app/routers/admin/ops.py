from __future__ import annotations

import os
import requests
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
}


def _run_inline_migrations() -> None:
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
            subprocess.run(["python", str(rls_py), "--schema", "public", "--set-default"], check=True, cwd=str(root), env=env)
        log.info("Inline migrations completed successfully")
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": True,
            "error": None,
        })
    except subprocess.CalledProcessError as e:
        log.error("inline_migration_failed: %s", e)
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": f"inline_migration_failed:{e}",
        })
    except Exception as e:
        log.exception("inline_migration_error: %s", e)
        migration_state.update({
            "running": False,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ok": False,
            "error": f"inline_migration_error:{e}",
        })


@router.post("/ops/migrate")
def trigger_migrations(background_tasks: BackgroundTasks):
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
            background_tasks.add_task(_run_inline_migrations)
            return {"ok": True, "mode": "inline_async", "started": True}
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
        migration_state.update({
            "running": True,
            "mode": "render_job",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "ok": None,
            "error": None,
        })
        return {"ok": True, "job_id": job_id}
    raise HTTPException(status_code=502, detail=f"render_api_error:{resp.status_code}")


@router.get("/ops/migrate/status")
def migrate_status():
    return migration_state


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
