from types import SimpleNamespace

from fastapi import BackgroundTasks
from sqlalchemy import text


def _ops_module():
    from app.routers.admin import ops as admin_ops

    return admin_ops


def _reset_migration_state() -> None:
    admin_ops = _ops_module()
    admin_ops.migration_state.update(
        {
            "running": False,
            "mode": None,
            "started_at": None,
            "finished_at": None,
            "ok": None,
            "error": None,
            "run_id": None,
        }
    )


def _reset_migration_tables(db) -> None:
    db.execute(text("DROP TABLE IF EXISTS admin_migration_runs"))
    db.execute(text("DROP TABLE IF EXISTS _migrations"))
    db.commit()


def test_admin_ops_migrate_runs_idempotent_script_and_logs_history(
    db,
    monkeypatch,
):
    admin_ops = _ops_module()
    _reset_migration_state()
    _reset_migration_tables(db)
    calls: list[dict[str, object]] = []

    def fake_run(cmd, cwd=None, env=None, capture_output=False, text=False):
        calls.append(
            {
                "cmd": cmd,
                "cwd": cwd,
                "database_url": None if env is None else env.get("DATABASE_URL"),
                "capture_output": capture_output,
                "text": text,
            }
        )
        return SimpleNamespace(returncode=0, stdout="[SUCCESS] All applicable migration(s) processed!", stderr="")

    monkeypatch.setattr(admin_ops.subprocess, "run", fake_run)

    background_tasks = BackgroundTasks()
    payload = admin_ops.trigger_migrations(background_tasks=background_tasks, db=db)
    assert payload["ok"] is True
    assert payload["started"] is True
    assert payload["mode"] == "sql_idempotent_async"
    assert payload["runner"] == "ops/scripts/migrate_all_migrations_idempotent.py"
    assert len(background_tasks.tasks) == 1

    for task in background_tasks.tasks:
        task.func(*task.args, **task.kwargs)

    assert len(calls) == 1
    cmd = calls[0]["cmd"]
    assert isinstance(cmd, list)
    assert any("migrate_all_migrations_idempotent.py" in str(part) for part in cmd)
    assert calls[0]["capture_output"] is True
    assert calls[0]["text"] is True

    status_payload = admin_ops.migrate_status(db=db)
    assert status_payload["running"] is False
    assert bool(status_payload["ok"]) is True
    assert status_payload["mode"] == "sql_idempotent_async"

    history = admin_ops.migrate_history(limit=5, db=db)
    items = history["items"]
    assert len(items) >= 1
    assert items[0]["mode"] == "sql_idempotent_async"
    assert bool(items[0]["ok"]) is True


def test_admin_ops_migrate_returns_noop_when_sql_migrations_are_already_tracked(
    db,
    monkeypatch,
):
    admin_ops = _ops_module()
    _reset_migration_state()
    _reset_migration_tables(db)

    monkeypatch.setattr(
        admin_ops,
        "_sql_migrations_status",
        lambda db=None: (False, 0, [], 7),
    )

    payload = admin_ops.trigger_migrations(background_tasks=BackgroundTasks(), db=db)
    assert payload == {
        "ok": True,
        "mode": "noop",
        "started": False,
        "message": "sin_migraciones_pendientes",
        "pending": False,
        "pending_count": 0,
        "pending_revisions": [],
        "applied_count": 7,
    }
