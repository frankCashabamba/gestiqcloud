"""HISTORICAL Module: Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class HistImportOut(BaseModel):
    id: UUID
    filename: str
    file_type: str | None = None
    file_size_bytes: int | None = None
    import_type: str
    total_rows: int = 0
    imported_rows: int = 0
    failed_rows: int = 0
    status: str = "pending"
    error_detail: str | None = None
    imported_by: UUID | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HistSaleOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    date: date
    number: str | None = None
    customer_code: str | None = None
    customer_name: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "USD"
    created_at: datetime

    class Config:
        from_attributes = True


class HistPurchaseOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    date: date
    number: str | None = None
    supplier_code: str | None = None
    supplier_name: str | None = None
    product_code: str | None = None
    product_name: str | None = None
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    currency: str = "USD"
    created_at: datetime

    class Config:
        from_attributes = True


class HistStockOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    date: date
    product_code: str | None = None
    product_name: str | None = None
    quantity: Decimal = Decimal("0")
    unit_cost: Decimal = Decimal("0")
    total_value: Decimal = Decimal("0")
    warehouse: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class HistDailySalesOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    date: date
    sales_total: Decimal = Decimal("0")
    total_items: int = 0
    avg_ticket: Decimal = Decimal("0")
    created_at: datetime

    class Config:
        from_attributes = True


class HistDashboardOut(BaseModel):
    total_imports: int = 0
    total_sales_records: int = 0
    total_purchase_records: int = 0
    total_stock_records: int = 0
    sales_total: Decimal = Decimal("0")
    purchases_total: Decimal = Decimal("0")
    date_range_from: date | None = None
    date_range_to: date | None = None


class PaginatedResponse(BaseModel):
    items: list = []
    total: int = 0
    page: int = 1
    page_size: int = 50
