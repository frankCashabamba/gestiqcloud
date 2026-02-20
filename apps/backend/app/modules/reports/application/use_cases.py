"""Use cases for Reports module."""

import logging
import uuid
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.reports.domain.entities import (
    ReportDefinition,
    ReportFormat,
    ReportFrequency,
    ReportType,
)
from app.modules.reports.infrastructure.report_generator import ReportService

logger = logging.getLogger(__name__)


class GenerateReportUseCase:
    """Generate a report and return its data."""

    def execute(
        self,
        db: Session,
        tenant_id: str,
        report_type: ReportType,
        name: str,
        export_format: ReportFormat = ReportFormat.JSON,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        filters: dict | None = None,
    ) -> dict:
        definition = ReportDefinition(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=name,
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            filters=filters,
        )

        service = ReportService(db)
        generator = service.generators.get(report_type)
        if not generator:
            raise ValueError(f"Unsupported report type: {report_type}")

        data = generator.generate(definition, db)

        # Track in DB
        report_id = uuid.uuid4()
        now = datetime.utcnow()
        try:
            db.execute(
                text(
                    """INSERT INTO reports (id, tenant_id, name, report_type, format, status, row_count, created_at, updated_at)
                    VALUES (:id, :tenant_id, :name, :report_type, :format, :status, :row_count, :created_at, :updated_at)"""
                ),
                {
                    "id": str(report_id),
                    "tenant_id": tenant_id,
                    "name": name,
                    "report_type": report_type.value,
                    "format": export_format.value,
                    "status": "ready",
                    "row_count": len(data.rows),
                    "created_at": now,
                    "updated_at": now,
                },
            )
            db.commit()
        except Exception:
            logger.debug("Could not persist report record (table may not exist yet)")
            db.rollback()

        return {
            "id": str(report_id),
            "name": name,
            "report_type": report_type.value,
            "format": export_format.value,
            "status": "ready",
            "row_count": len(data.rows),
            "data": data.to_dict(),
        }


class ListReportsUseCase:
    """List generated reports for a tenant."""

    def execute(self, db: Session, tenant_id: str) -> dict:
        try:
            rows = db.execute(
                text("""SELECT id, name, report_type, format, status, row_count, created_at
                    FROM reports WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC LIMIT 100"""),
                {"tenant_id": tenant_id},
            ).fetchall()

            items = [
                {
                    "id": str(r[0]),
                    "name": r[1],
                    "report_type": r[2],
                    "format": r[3],
                    "status": r[4],
                    "row_count": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                }
                for r in rows
            ]
            return {"items": items, "total": len(items)}
        except Exception:
            logger.debug("Reports table not available, returning empty list")
            return {"items": [], "total": 0}


class ExportReportUseCase:
    """Generate and export a report to the specified format."""

    def execute(
        self,
        db: Session,
        tenant_id: str,
        report_type: ReportType,
        export_format: ReportFormat,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        filters: dict | None = None,
    ) -> bytes:
        definition = ReportDefinition(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=f"{report_type.value}_export",
            report_type=report_type,
            date_from=date_from,
            date_to=date_to,
            filters=filters,
        )

        service = ReportService(db)
        return service.generate_report(definition, export_format)


class ScheduleReportUseCase:
    """Create a scheduled report configuration."""

    def execute(
        self,
        db: Session,
        tenant_id: str,
        report_type: ReportType,
        name: str,
        export_format: ReportFormat,
        frequency: ReportFrequency,
        recipients: list[str],
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        import json

        schedule_id = uuid.uuid4()
        now = datetime.utcnow()

        try:
            db.execute(
                text(
                    """INSERT INTO scheduled_reports
                    (id, tenant_id, name, report_type, format, frequency, recipients, is_active, created_at, updated_at)
                    VALUES (:id, :tenant_id, :name, :report_type, :format, :frequency, :recipients, :is_active, :created_at, :updated_at)"""
                ),
                {
                    "id": str(schedule_id),
                    "tenant_id": tenant_id,
                    "name": name,
                    "report_type": report_type.value,
                    "format": export_format.value,
                    "frequency": frequency.value,
                    "recipients": json.dumps(recipients),
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create scheduled report: {e}")
            raise

        return {
            "id": str(schedule_id),
            "name": name,
            "report_type": report_type.value,
            "format": export_format.value,
            "frequency": frequency.value,
            "recipients": recipients,
            "is_active": True,
            "next_scheduled_at": None,
        }


class ListScheduledReportsUseCase:
    """List scheduled reports for a tenant."""

    def execute(self, db: Session, tenant_id: str) -> list[dict]:
        try:
            rows = db.execute(
                text(
                    """SELECT id, name, report_type, format, frequency, recipients, is_active, next_scheduled_at
                    FROM scheduled_reports WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC"""
                ),
                {"tenant_id": tenant_id},
            ).fetchall()

            import json

            return [
                {
                    "id": str(r[0]),
                    "name": r[1],
                    "report_type": r[2],
                    "format": r[3],
                    "frequency": r[4],
                    "recipients": json.loads(r[5]) if isinstance(r[5], str) else (r[5] or []),
                    "is_active": r[6],
                    "next_scheduled_at": r[7].isoformat() if r[7] else None,
                }
                for r in rows
            ]
        except Exception:
            logger.debug("Scheduled reports table not available")
            return []


class DeleteScheduledReportUseCase:
    """Delete a scheduled report."""

    def execute(self, db: Session, tenant_id: str, schedule_id: str) -> bool:
        result = db.execute(
            text("""DELETE FROM scheduled_reports
                WHERE id = :id AND tenant_id = :tenant_id"""),
            {"id": schedule_id, "tenant_id": tenant_id},
        )
        db.commit()
        return result.rowcount > 0
