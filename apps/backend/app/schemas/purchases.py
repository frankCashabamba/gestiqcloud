"""Purchases Pydantic schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PurchaseStatus = Literal["draft", "sent", "received", "cancelled"]


class PurchaseBase(BaseModel):
    """Common purchase fields."""

    number: str = Field(..., max_length=50, description="Purchase number")
    supplier_id: UUID | None = Field(None, description="Supplier ID")
    date: date = Field(default_factory=date.today)
    subtotal: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)
    status: PurchaseStatus = Field(default="draft")
    notes: str | None = None

    model_config = ConfigDict()


class PurchaseCreate(PurchaseBase):
    """Create purchase."""


class PurchaseUpdate(BaseModel):
    """Update purchase (all fields optional)."""

    number: str | None = Field(None, max_length=50)
    supplier_id: UUID | None = Field(None)
    date: date | None = Field(None)
    subtotal: float | None = Field(None, ge=0)
    taxes: float | None = Field(None, ge=0)
    total: float | None = Field(None, ge=0)
    status: PurchaseStatus | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class PurchaseResponse(PurchaseBase):
    """Purchase response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseList(BaseModel):
    """Paginated purchase list."""

    items: list[PurchaseResponse]
    total: int
    page: int = 1
    page_size: int = 100


class PurchaseLineBase(BaseModel):
    """Common purchase line fields."""

    product_id: UUID = Field(..., description="Product ID")
    quantity: float = Field(..., gt=0, description="Quantity")
    unit_price: float = Field(..., ge=0, description="Unit price")
    tax_rate: float = Field(default=0, ge=0, le=1, description="Tax rate (0-1)")
    discount: float = Field(default=0, ge=0, le=100, description="Discount %")
    total: float = Field(default=0, ge=0, description="Line total")


class PurchaseLineCreate(PurchaseLineBase):
    """Create purchase line."""

    purchase_id: UUID = Field(..., description="Purchase ID")


class PurchaseLineResponse(PurchaseLineBase):
    """Purchase line response."""

    id: UUID
    purchase_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
