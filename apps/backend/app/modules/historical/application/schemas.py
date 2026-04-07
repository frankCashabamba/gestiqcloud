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
    fecha: date
    numero: str | None = None
    cliente_code: str | None = None
    cliente_nombre: str | None = None
    producto_code: str | None = None
    producto_nombre: str | None = None
    cantidad: Decimal = Decimal("0")
    precio_unitario: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")
    impuesto: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    moneda: str = "USD"
    created_at: datetime

    class Config:
        from_attributes = True


class HistPurchaseOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    fecha: date
    numero: str | None = None
    proveedor_code: str | None = None
    proveedor_nombre: str | None = None
    producto_code: str | None = None
    producto_nombre: str | None = None
    cantidad: Decimal = Decimal("0")
    precio_unitario: Decimal = Decimal("0")
    subtotal: Decimal = Decimal("0")
    impuesto: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    moneda: str = "USD"
    created_at: datetime

    class Config:
        from_attributes = True


class HistStockOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    fecha: date
    producto_code: str | None = None
    producto_nombre: str | None = None
    cantidad: Decimal = Decimal("0")
    costo_unitario: Decimal = Decimal("0")
    valor_total: Decimal = Decimal("0")
    almacen: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class HistDailySalesOut(BaseModel):
    id: UUID
    import_id: UUID | None = None
    fecha: date
    total_ventas: Decimal = Decimal("0")
    total_items: int = 0
    ticket_promedio: Decimal = Decimal("0")
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
