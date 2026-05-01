"""Celery tasks for the Reports module.

Two tasks are exposed:

* ``process_due_scheduled_reports``: scans ``scheduled_reports`` for active
  configurations whose ``next_scheduled_at`` (a.k.a. ``next_run_at`` in the
  task spec) is due, executes the corresponding generator, persists a new
  row in ``reports`` and advances ``next_scheduled_at`` based on
  ``cron_expression`` (when present) or ``frequency``.
* ``recalculate_profit_snapshots``: nightly per-tenant recomputation of
  profit snapshots delegating to ``RecalculationService``.

Both tasks are registered unconditionally so they remain invokable from
shells / management endpoints. Whether they are *scheduled* by Celery beat
is gated by the ``REPORTS_SCHEDULER_ENABLED`` env flag (see
``apps/backend/celery_app.py``).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from apps.backend.celery_app import celery_app
except Exception:  # pragma: no cover - alternate import path
    from celery_app import celery_app  # type: ignore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_FREQUENCY_DELTAS: dict[str, timedelta] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=90),
    "yearly": timedelta(days=365),
}


def _next_run_from_frequency(now: datetime, frequency: str | None) -> datetime | None:
    """Compute the next run timestamp from a frequency string.

    Returns ``None`` for ``custom`` / unknown frequencies so the caller can
    decide what to do (typically: leave ``next_scheduled_at`` untouched and
    log a warning).
    """
    if not frequency:
        return None
    delta = _FREQUENCY_DELTAS.get(frequency.lower())
    if delta is None:
        return None
    return now + delta


def _next_run_from_cron(now: datetime, cron_expression: str | None) -> datetime | None:
    """Compute the next run timestamp from a cron expression.

    Uses ``croniter`` if available; otherwise returns ``None`` so the caller
    falls back to frequency-based scheduling.
    """
    if not cron_expression:
        return None
    try:
        from croniter import croniter  # type: ignore

        return croniter(cron_expression, now).get_next(datetime)
    except Exception:  # pragma: no cover - croniter optional
        logger.warning(
            "croniter not available or invalid cron expression %r", cron_expression
        )
        return None


def _open_session() -> Session:
    """Open a SQLAlchemy session for use inside a task."""
    from app.config.database import SessionLocal  # local import to avoid app boot at import-time

    return SessionLocal()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(name="apps.backend.app.workers.reports_tasks.process_due_scheduled_reports")
def process_due_scheduled_reports() -> dict[str, Any]:
    """Process every ``scheduled_reports`` row whose run time has elapsed.

    Returns a small summary dict useful for tests and observability.
    """
    from app.modules.reports.application.use_cases import GenerateReportUseCase
    from app.modules.reports.domain.entities import ReportFormat, ReportType

    session = _open_session()
    summary: dict[str, Any] = {"processed": 0, "errors": 0, "ids": []}
    try:
        now = datetime.now(UTC)

        rows = session.execute(
            text(
                """
                SELECT id, tenant_id, name, report_type, format, frequency,
                       recipients, cron_expression, next_scheduled_at
                FROM scheduled_reports
                WHERE is_active = TRUE
                  AND (next_scheduled_at IS NULL OR next_scheduled_at <= :now)
                """
            ),
            {"now": now},
        ).fetchall()

        for row in rows:
            schedule_id = str(row[0])
            tenant_id = str(row[1])
            name = row[2]
            report_type_value = row[3]
            export_format_value = row[4]
            frequency = row[5]
            cron_expression = row[7] if len(row) > 7 else None

            try:
                report_type = ReportType(report_type_value)
                export_format = ReportFormat(export_format_value)
            except ValueError:
                logger.error(
                    "Invalid report_type/format on scheduled_reports id=%s", schedule_id
                )
                summary["errors"] += 1
                continue

            try:
                uc = GenerateReportUseCase()
                uc.execute(
                    db=session,
                    tenant_id=tenant_id,
                    report_type=report_type,
                    name=name,
                    export_format=export_format,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to generate scheduled report id=%s: %s", schedule_id, exc
                )
                summary["errors"] += 1
                continue

            next_run = _next_run_from_cron(now, cron_expression) or _next_run_from_frequency(
                now, frequency
            )

            session.execute(
                text(
                    """
                    UPDATE scheduled_reports
                    SET last_generated_at = :now,
                        next_scheduled_at = :next_run,
                        updated_at = :now
                    WHERE id = :id
                    """
                ),
                {"now": now, "next_run": next_run, "id": schedule_id},
            )

            summary["processed"] += 1
            summary["ids"].append(schedule_id)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return summary


@celery_app.task(name="apps.backend.app.workers.reports_tasks.recalculate_profit_snapshots")
def recalculate_profit_snapshots(target_date: str | None = None) -> dict[str, Any]:
    """Nightly per-tenant recompute of profit snapshots.

    ``target_date`` is an optional ISO date (``YYYY-MM-DD``); defaults to
    *yesterday* (UTC) so the nightly run captures the day that just closed.
    """
    from app.modules.reports.application.recalculation_service import RecalculationService

    if target_date is None:
        day = (datetime.now(UTC) - timedelta(days=1)).date()
    else:
        day = date.fromisoformat(target_date)

    session = _open_session()
    summary: dict[str, Any] = {"date": day.isoformat(), "tenants": 0, "errors": 0}
    try:
        # Discover tenants with sales activity for the target day. Falls back
        # silently if the table is missing (e.g. minimal test env).
        try:
            tenant_rows = session.execute(
                text(
                    """
                    SELECT DISTINCT tenant_id FROM sales_orders
                    WHERE order_date = :day
                    """
                ),
                {"day": day},
            ).fetchall()
        except Exception:
            logger.debug("sales_orders not available; skipping profit recalculation")
            return summary

        svc = RecalculationService(session)
        for (tenant_id,) in tenant_rows:
            try:
                tid = tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id))
                svc.recalculate_daily(tid, day)
                summary["tenants"] += 1
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception(
                    "Failed to recalc profit snapshot tenant=%s date=%s: %s",
                    tenant_id, day, exc,
                )
                summary["errors"] += 1

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return summary


__all__ = [
    "process_due_scheduled_reports",
    "recalculate_profit_snapshots",
]