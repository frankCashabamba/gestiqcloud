"""Reports endpoints - Tenant."""

import io
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import ensure_tenant, get_current_user
from app.modules.reports.application.schemas import (
    ExportRequest,
    GenerateReportRequest,
    ScheduleReportRequest,
)
from app.modules.reports.application.use_cases import (
    DeleteScheduledReportUseCase,
    ExportReportUseCase,
    GenerateReportUseCase,
    ListReportsUseCase,
    ListScheduledReportsUseCase,
    ScheduleReportUseCase,
)
from app.modules.reports.domain.entities import ReportFormat, ReportType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

CONTENT_TYPES = {
    ReportFormat.CSV: "text/csv",
    ReportFormat.EXCEL: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ReportFormat.PDF: "application/pdf",
    ReportFormat.JSON: "application/json",
    ReportFormat.HTML: "text/html",
}

FILE_EXTENSIONS = {
    ReportFormat.CSV: "csv",
    ReportFormat.EXCEL: "xlsx",
    ReportFormat.PDF: "pdf",
    ReportFormat.JSON: "json",
    ReportFormat.HTML: "html",
}


@router.post("/generate")
def generate_report(
    payload: GenerateReportRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Generate a report and return JSON data."""
    try:
        uc = GenerateReportUseCase()
        result = uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=payload.report_type,
            name=payload.name,
            export_format=payload.format,
            date_from=payload.date_from,
            date_to=payload.date_to,
            filters=payload.filters,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail="Error generating report")


@router.get("")
def list_report_types(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """List available report types and previously generated reports."""
    available_types = [
        {"value": rt.value, "label": rt.value.replace("_", " ").title()}
        for rt in ReportType
    ]
    uc = ListReportsUseCase()
    history = uc.execute(db, tenant_id)
    return {
        "available_types": available_types,
        "history": history,
    }


@router.post("/export")
def export_report(
    payload: ExportRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Export a report to a file format and return as download."""
    try:
        uc = ExportReportUseCase()
        content = uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=payload.report_type,
            export_format=payload.format,
            date_from=payload.date_from,
            date_to=payload.date_to,
            filters=payload.filters,
        )

        content_type = CONTENT_TYPES.get(payload.format, "application/octet-stream")
        extension = FILE_EXTENSIONS.get(payload.format, "bin")
        filename = f"{payload.report_type.value}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{extension}"

        return StreamingResponse(
            io.BytesIO(content),
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=500, detail="Error exporting report")


@router.get("/sales")
def get_sales_report(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    """Generate sales report with date filters."""
    try:
        uc = GenerateReportUseCase()
        return uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=ReportType.SALES_SUMMARY,
            name="Sales Report",
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        logger.error(f"Failed to generate sales report: {e}")
        raise HTTPException(status_code=500, detail="Error generating sales report")


@router.get("/inventory")
def get_inventory_report(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Generate inventory report."""
    try:
        uc = GenerateReportUseCase()
        return uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=ReportType.INVENTORY_STATUS,
            name="Inventory Report",
        )
    except Exception as e:
        logger.error(f"Failed to generate inventory report: {e}")
        raise HTTPException(status_code=500, detail="Error generating inventory report")


@router.get("/financial")
def get_financial_report(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    """Generate financial (P&L) report."""
    try:
        uc = GenerateReportUseCase()
        return uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=ReportType.PROFIT_LOSS,
            name="Financial Report",
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        logger.error(f"Failed to generate financial report: {e}")
        raise HTTPException(status_code=500, detail="Error generating financial report")


@router.post("/schedule")
def create_scheduled_report(
    payload: ScheduleReportRequest,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Create a scheduled report configuration."""
    try:
        uc = ScheduleReportUseCase()
        return uc.execute(
            db=db,
            tenant_id=tenant_id,
            report_type=payload.report_type,
            name=payload.name,
            export_format=payload.format,
            frequency=payload.frequency,
            recipients=payload.recipients,
            date_from=payload.date_from,
            date_to=payload.date_to,
        )
    except Exception as e:
        logger.error(f"Failed to create scheduled report: {e}")
        raise HTTPException(status_code=500, detail="Error creating scheduled report")


@router.get("/scheduled")
def list_scheduled_reports(
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """List scheduled reports for the tenant."""
    uc = ListScheduledReportsUseCase()
    return uc.execute(db, tenant_id)


@router.delete("/scheduled/{schedule_id}")
def delete_scheduled_report(
    schedule_id: UUID,
    tenant_id: str = Depends(ensure_tenant),
    db: Session = Depends(get_db),
):
    """Delete a scheduled report."""
    uc = DeleteScheduledReportUseCase()
    deleted = uc.execute(db, tenant_id, str(schedule_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Scheduled report not found")
    return {"status": "deleted", "id": str(schedule_id)}
