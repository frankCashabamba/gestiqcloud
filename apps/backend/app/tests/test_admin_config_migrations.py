import asyncio

from fastapi import BackgroundTasks
from sqlalchemy import text


def _legacy_module():
    from app.modules.admin_config.interface.http import migrations as legacy_migrations

    return legacy_migrations


def _ops_module():
    from app.routers.admin import ops as admin_ops

    return admin_ops


def test_legacy_execute_delegates_to_admin_ops_runner(db, monkeypatch):
    legacy_migrations = _legacy_module()
    admin_ops = _ops_module()
    calls: list[dict[str, object]] = []

    def fake_trigger_migrations(*, background_tasks, db):
        calls.append({"background_tasks": background_tasks, "db": db})
        return {
            "ok": True,
            "started": True,
            "run_id": "run-123",
            "mode": "sql_idempotent_async",
        }

    monkeypatch.setattr(admin_ops, "trigger_migrations", fake_trigger_migrations)

    response = asyncio.run(
        legacy_migrations.execute_migrations(background_tasks=BackgroundTasks(), db=db)
    )

    assert response.ok is True
    assert response.job_id == "run-123"
    assert response.message == "Migrations in progress (idempotent runner)"
    assert response.migrations_applied == 0
    assert len(calls) == 1
    assert calls[0]["db"] is db


def test_schema_migrations_syncs_applied_and_pending_disk_migrations(db, monkeypatch):
    legacy_migrations = _legacy_module()

    db.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    db.execute(text("DROP TABLE IF EXISTS _migrations"))
    db.commit()

    monkeypatch.setattr(
        legacy_migrations,
        "list_sql_migration_names",
        lambda: ["2026-03-01_000_first_change", "2026-03-02_000_second_change"],
    )
    monkeypatch.setattr(
        legacy_migrations,
        "load_applied_sql_migration_names",
        lambda _db: {"2026-03-01_000_first_change"},
    )

    legacy_migrations._ensure_schema_migrations_table(db)

    rows = db.execute(
        text("SELECT version, name, status FROM schema_migrations ORDER BY version")
    ).mappings()
    items = {row["version"]: dict(row) for row in rows}

    assert items["2026-03-01_000_first_change"]["name"] == "first_change"
    assert items["2026-03-01_000_first_change"]["status"] == "success"
    assert items["2026-03-02_000_second_change"]["name"] == "second_change"
    assert items["2026-03-02_000_second_change"]["status"] == "pending"


def test_schema_migrations_sync_preserves_ignored_rows_until_applied(db, monkeypatch):
    legacy_migrations = _legacy_module()

    db.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    db.execute(text("DROP TABLE IF EXISTS _migrations"))
    db.commit()

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                hash VARCHAR(64),
                applied_at TIMESTAMP
            )
            """
        )
    )
    schema_id_type = "SERIAL PRIMARY KEY" if db.get_bind().dialect.name == "postgresql" else "INTEGER PRIMARY KEY"
    db.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id {schema_id_type},
                version VARCHAR NOT NULL UNIQUE,
                name VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'pending',
                mode VARCHAR,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                executed_by VARCHAR,
                execution_time_ms INTEGER,
                error_message TEXT,
                applied_order INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            """
            INSERT INTO schema_migrations (version, name, status, created_at, updated_at)
            VALUES ('2026-03-02_000_second_change', 'second_change', 'ignored', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )
    )
    db.commit()

    monkeypatch.setattr(
        legacy_migrations,
        "list_sql_migration_names",
        lambda: ["2026-03-02_000_second_change"],
    )
    monkeypatch.setattr(legacy_migrations, "load_applied_sql_migration_names", lambda _db: set())

    legacy_migrations._ensure_schema_migrations_table(db)
    status_before_apply = db.execute(
        text("SELECT status FROM schema_migrations WHERE version = '2026-03-02_000_second_change'")
    ).scalar_one()
    assert status_before_apply == "ignored"

    monkeypatch.setattr(
        legacy_migrations,
        "load_applied_sql_migration_names",
        lambda _db: {"2026-03-02_000_second_change"},
    )
    legacy_migrations._ensure_schema_migrations_table(db)
    status_after_apply = db.execute(
        text("SELECT status FROM schema_migrations WHERE version = '2026-03-02_000_second_change'")
    ).scalar_one()
    assert status_after_apply == "success"
