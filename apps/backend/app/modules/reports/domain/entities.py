"""Reports domain entities"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class ReportType(str, Enum):
    """Report types"""

    SALES_SUMMARY = "sales_summary"
    SALES_DETAIL = "sales_detail"
    INVENTORY_STATUS = "inventory_status"
    INVENTORY_MOVEMENT = "inventory_movement"
    CASH_FLOW = "cash_flow"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    ACCOUNTS_PAYABLE = "accounts_payable"
    PROFIT_LOSS = "profit_loss"
    BALANCE_SHEET = "balance_sheet"
    TAX_SUMMARY = "tax_summary"
    CUSTOMER_ANALYSIS = "customer_analysis"
    PRODUCT_ANALYSIS = "product_analysis"
    PURCHASE_ANALYSIS = "purchase_analysis"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Export formats"""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class ReportStatus(str, Enum):
    """Report generation status"""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class ReportFrequency(str, Enum):
    """Report frequency for scheduled reports"""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class ReportDefinition:
    """Report definition/configuration"""

    id: UUID
    tenant_id: str
    name: str
    description: str | None = None
    report_type: ReportType = ReportType.CUSTOM
    date_from: datetime | None = None
    date_to: datetime | None = None
    filters: dict[str, Any] | None = None  # Custom filters
    group_by: list[str] | None = None
    columns: list[str] | None = None
    sort_by: dict[str, str] | None = None  # {column: 'asc'|'desc'}
    include_totals: bool = True
    include_charts: bool = False
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class Report:
    """Generated report"""

    id: UUID
    tenant_id: str
    definition_id: UUID
    report_type: ReportType
    format: ReportFormat
    status: ReportStatus = ReportStatus.PENDING
    file_path: str | None = None
    file_size: int | None = None
    row_count: int | None = None
    download_url: str | None = None
    generated_at: datetime | None = None
    expires_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class ScheduledReport:
    """Scheduled report configuration"""

    id: UUID
    tenant_id: str
    definition_id: UUID
    report_format: ReportFormat
    frequency: ReportFrequency
    recipients: list[str]  # Email addresses
    is_active: bool = True
    last_generated_at: datetime | None = None
    next_scheduled_at: datetime | None = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class ReportData:
    """Report data structure"""

    columns: list[str]
    rows: list[list[Any]]
    totals: dict[str, Any] | None = None
    summary: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "totals": self.totals,
            "summary": self.summary,
            "metadata": self.metadata,
        }


@dataclass
class SalesReport(ReportData):
    """Sales report specific data"""

    total_sales: float = 0.0
    total_items: int = 0
    average_order_value: float = 0.0
    order_count: int = 0


@dataclass
class InventoryReport(ReportData):
    """Inventory report specific data"""

    total_items: int = 0
    low_stock_count: int = 0
    out_of_stock_count: int = 0
    total_value: float = 0.0


@dataclass
class FinancialReport(ReportData):
    """Financial report specific data"""

    total_revenue: float = 0.0
    total_expenses: float = 0.0
    net_profit: float = 0.0
    profit_margin: float = 0.0


@dataclass
class ReportFilter:
    """Report filter specification"""

    field: str
    operator: str  # 'eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'contains'
    value: Any

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value,
        }
