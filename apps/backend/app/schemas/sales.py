"""Sales Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Base schema
class SaleBase(BaseModel):
    """Common sales fields."""

    number: str = Field(..., alias="numero", max_length=50, description="Sale number")
    customer_id: UUID | None = Field(None, alias="cliente_id", description="Customer ID")
    date: date = Field(default_factory=date.today, alias="fecha")
    subtotal: float = Field(default=0, ge=0)
    taxes: float = Field(default=0, ge=0, alias="impuestos")
    total: float = Field(default=0, ge=0)
    status: str = Field(
        default="draft",
        alias="estado",
        pattern="^(draft|confirmed|invoiced|cancelled)$",
    )
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(populate_by_name=True)


class SaleCreate(SaleBase):
    """Create sale schema."""


class SaleUpdate(BaseModel):
    """Update sale schema (all fields optional)."""

    number: str | None = Field(None, alias="numero", max_length=50)
    customer_id: UUID | None = Field(None, alias="cliente_id")
    date: date | None = Field(None, alias="fecha")
    subtotal: float | None = Field(None, ge=0)
    taxes: float | None = Field(None, alias="impuestos", ge=0)
    total: float | None = Field(None, ge=0)
    status: str | None = Field(
        None, alias="estado", pattern="^(draft|confirmed|invoiced|cancelled)$"
    )
    notes: str | None = Field(None, alias="notas")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SaleResponse(SaleBase):
    """Sale response schema."""

    id: UUID
    tenant_id: UUID
    user_id: UUID = Field(alias="usuario_id")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SaleList(BaseModel):
    """Paginated sale list."""

    items: list[SaleResponse]
    total: int
    page: int = 1
    page_size: int = 100
