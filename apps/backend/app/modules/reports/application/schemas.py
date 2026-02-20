"""Pydantic schemas for Reports module."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.reports.domain.entities import ReportFormat, ReportFrequency, ReportType


class GenerateReportRequest(BaseModel):
    report_type: ReportType
    name: str
    date_from: datetime | None = None
    date_to: datetime | None = None
    filters: dict | None = None
    format: ReportFormat = ReportFormat.JSON


class ReportResponse(BaseModel):
    id: UUID
    name: str
    report_type: str
    format: str
    status: str
    row_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportResponse]
    total: int


class ReportDataResponse(BaseModel):
    columns: list[str]
    rows: list[list]
    summary: dict | None = None
    metadata: dict | None = None


class ScheduleReportRequest(BaseModel):
    report_type: ReportType
    name: str
    format: ReportFormat = ReportFormat.PDF
    frequency: ReportFrequency
    recipients: list[str]
    date_from: datetime | None = None
    date_to: datetime | None = None


class ScheduledReportResponse(BaseModel):
    id: UUID
    name: str
    report_type: str
    format: str
    frequency: str
    recipients: list[str]
    is_active: bool
    next_scheduled_at: datetime | None = None

    model_config = {"from_attributes": True}


class ExportRequest(BaseModel):
    report_type: ReportType
    format: ReportFormat = ReportFormat.CSV
    date_from: datetime | None = None
    date_to: datetime | None = None
    filters: dict | None = None
