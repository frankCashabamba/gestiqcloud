"""Purchases Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseBase(BaseModel):
    """Common purchase fields."""

    number: str = Field(..., alias="numero", max_length=50, description="Purchase number")
    supplier_id: UUID | None = Field(None, description="Supplier ID")
    date: date = Field(default_factory=date.today, alias="fecha")
    subtotal: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0, alias="impuestos")
    total: float = Field(default=0, ge=0)
    status: str = Field(
        default="draft",
        alias="estado",
        pattern="^(draft|confirmed|received|cancelled)$",
    )
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(populate_by_name=True)


class PurchaseCreate(PurchaseBase):
    """Create purchase."""


class PurchaseUpdate(BaseModel):
    """Update purchase (all fields optional)."""

    number: str | None = Field(None, alias="numero", max_length=50)
    supplier_id: UUID | None = Field(None)
    date: date | None = Field(None, alias="fecha")
    subtotal: float | None = Field(None, ge=0)
    taxes: float | None = Field(None, alias="impuestos", ge=0)
    total: float | None = Field(None, ge=0)
    status: str | None = Field(
        None, alias="estado", pattern="^(draft|confirmed|received|cancelled)$"
    )
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class PurchaseResponse(PurchaseBase):
    """Purchase response."""

    id: UUID
    tenant_id: UUID
    user_id: UUID = Field(alias="usuario_id")
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

    product_id: UUID = Field(..., alias="producto_id", description="Product ID")
    quantity: float = Field(..., alias="cantidad", gt=0, description="Quantity")
    unit_price: float = Field(..., alias="precio_unitario", ge=0, description="Unit price")
    tax_rate: float = Field(
        default=0, alias="impuesto_tasa", ge=0, le=1, description="Tax rate (0-1)"
    )
    discount: float = Field(default=0, alias="descuento", ge=0, le=100, description="Discount %")
    total: float = Field(default=0, ge=0, description="Line total")


class PurchaseLineCreate(PurchaseLineBase):
    """Create purchase line."""

    purchase_id: UUID = Field(..., alias="compra_id", description="Purchase ID")


class PurchaseLineResponse(PurchaseLineBase):
    """Purchase line response."""

    id: UUID
    purchase_id: UUID = Field(alias="compra_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
