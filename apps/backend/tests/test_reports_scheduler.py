"""Tests for ``apps.backend.app.workers.reports_tasks.process_due_scheduled_reports``.

The task scans ``scheduled_reports`` for active rows whose ``next_scheduled_at``
is past-due, runs the corresponding generator and bumps ``next_scheduled_at``
according to ``cron_expression`` (when present) or ``frequency``.

These tests stub out the actual report generation (``GenerateReportUseCase``)
so they can run on the SQLite test database without touching the full sales
graph, and assert the scheduler's selection + ``next_scheduled_at`` rollover
behavior.
"""

from __future__ import annotations

import uuid
import importlib
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest
from sqlalchemy import text


def _ensure_scheduled_reports_table(db) -> None:
    """Create a SQLite-friendly ``scheduled_reports`` table for the test DB."""
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS scheduled_reports (
                id                TEXT PRIMARY KEY,
                tenant_id         TEXT NOT NULL,
                name              TEXT NOT NULL,
                report_type       TEXT NOT NULL,
                format            TEXT NOT NULL,
                frequency         TEXT,
                cron_expression   TEXT,
                recipients        TEXT NOT NULL DEFAULT '[]',
                is_active         INTEGER NOT NULL DEFAULT 1,
                last_generated_at TIMESTAMP,
                next_scheduled_at TIMESTAMP,
                created_at        TIMESTAMP NOT NULL,
                updated_at        TIMESTAMP NOT NULL
            )
            """
        )
    )
    db.execute(text("DELETE FROM scheduled_reports"))


def _insert_schedule(
    db,
    *,
    schedule_id: str,
    tenant_id: str,
    is_active: bool,
    next_scheduled_at: datetime | None,
    frequency: str = "daily",
    cron_expression: str | None = None,
) -> None:
    now = datetime.now(UTC)
    db.execute(
        text(
            """
            INSERT INTO scheduled_reports
              (id, tenant_id, name, report_type, format, frequency,
               cron_expression, recipients, is_active, next_scheduled_at,
               created_at, updated_at)
            VALUES (:id, :tenant_id, :name, :rt, :fmt, :freq, :cron, '[]',
                    :is_active, :next_scheduled_at, :now, :now)
            """
        ),
        {
            "id": schedule_id,
            "tenant_id": tenant_id,
            "name": f"sched-{schedule_id[:8]}",
            "rt": "sales_summary",
            "fmt": "json",
            "freq": frequency,
            "cron": cron_expression,
            "is_active": is_active if db.get_bind().dialect.name == "postgresql" else (1 if is_active else 0),
            "next_scheduled_at": next_scheduled_at,
            "now": now,
        },
    )
    db.commit()


@pytest.fixture
def patched_session(db):
    """Patch ``_open_session`` so the task uses the test DB session."""
    from app.workers import reports_tasks

    class _NoCloseSession:
        """Wrap the test session and swallow .close() so pytest can clean up."""

        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            if name == "close":
                return lambda: None
            return getattr(self._inner, name)

    with mock.patch.object(
        reports_tasks, "_open_session", return_value=_NoCloseSession(db)
    ):
        yield db


def test_process_due_scheduled_reports_picks_due_rows(patched_session):
    """Only active rows with ``next_scheduled_at <= now`` should be processed."""
    db = patched_session
    _ensure_scheduled_reports_table(db)

    tenant = str(uuid.uuid4())
    due_id = str(uuid.uuid4())
    future_id = str(uuid.uuid4())
    inactive_id = str(uuid.uuid4())

    now = datetime.now(UTC)

    _insert_schedule(
        db,
        schedule_id=due_id,
        tenant_id=tenant,
        is_active=True,
        next_scheduled_at=now - timedelta(minutes=10),
        frequency="daily",
    )
    _insert_schedule(
        db,
        schedule_id=future_id,
        tenant_id=tenant,
        is_active=True,
        next_scheduled_at=now + timedelta(hours=1),
        frequency="daily",
    )
    _insert_schedule(
        db,
        schedule_id=inactive_id,
        tenant_id=tenant,
        is_active=False,
        next_scheduled_at=now - timedelta(minutes=10),
        frequency="daily",
    )

    from app.workers import reports_tasks

    # Stub the use-case so the scheduler isn't tied to the full sales graph.
    with mock.patch.object(
        importlib.import_module("app.modules.reports.application.use_cases"),
        "GenerateReportUseCase",
    ) as UC:
        UC.return_value.execute.return_value = {"id": "x"}
        summary = reports_tasks.process_due_scheduled_reports()

    assert summary["processed"] == 1
    assert summary["ids"] == [due_id]
    assert summary["errors"] == 0


def test_process_due_scheduled_reports_advances_next_scheduled_at(patched_session):
    """After a successful run ``next_scheduled_at`` must be pushed into the future
    using the row's frequency (daily ⇒ +1 day)."""
    db = patched_session
    _ensure_scheduled_reports_table(db)

    tenant = str(uuid.uuid4())
    sched_id = str(uuid.uuid4())
    past = datetime.now(UTC) - timedelta(hours=2)
    _insert_schedule(
        db,
        schedule_id=sched_id,
        tenant_id=tenant,
        is_active=True,
        next_scheduled_at=past,
        frequency="daily",
    )

    from app.workers import reports_tasks

    with mock.patch.object(
        importlib.import_module("app.modules.reports.application.use_cases"),
        "GenerateReportUseCase",
    ) as UC:
        UC.return_value.execute.return_value = {"id": "x"}
        before = datetime.now(UTC)
        before_local = datetime.now()
        reports_tasks.process_due_scheduled_reports()
        after = datetime.now(UTC)
        after_local = datetime.now()

    row = db.execute(
        text(
            "SELECT last_generated_at, next_scheduled_at FROM scheduled_reports WHERE id = :id"
        ),
        {"id": sched_id},
    ).first()

    assert row is not None
    last_gen, next_run = row[0], row[1]
    # SQLite returns naive datetimes; compare as naive.
    if isinstance(last_gen, str):
        last_gen = datetime.fromisoformat(last_gen)
    if isinstance(next_run, str):
        next_run = datetime.fromisoformat(next_run)
    assert last_gen is not None
    assert next_run is not None
    # next_run should be ~24h after the run timestamp (frequency=daily)
    delta = next_run - last_gen
    assert timedelta(hours=23, minutes=59) <= delta <= timedelta(hours=24, minutes=1)
    # And the run timestamp itself must fall inside the test execution window.
    if db.get_bind().dialect.name == "postgresql" and last_gen.tzinfo is None:
        naive_before = before_local
        naive_after = after_local
    else:
        naive_before = before.replace(tzinfo=None)
        naive_after = after.replace(tzinfo=None)
    assert naive_before - timedelta(seconds=1) <= last_gen <= naive_after + timedelta(seconds=1)
