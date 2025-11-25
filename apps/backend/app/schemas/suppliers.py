"""Pydantic schemas for Suppliers"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierContactCreate(BaseModel):
    """Schema for creating supplier contact"""

    name: str = Field(..., max_length=255)
    position: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)


class SupplierContactResponse(SupplierContactCreate):
    """Schema for supplier contact response"""

    id: UUID
    supplier_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierAddressCreate(BaseModel):
    """Schema for creating supplier address"""

    type: str | None = Field(None, pattern="^(billing|shipping|other)$")
    address: str | None = None
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country: str = Field(default="ES", max_length=2)


class SupplierAddressResponse(SupplierAddressCreate):
    """Schema for supplier address response"""

    id: UUID
    supplier_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    """Common Supplier fields"""

    code: str | None = Field(None, max_length=50)
    name: str = Field(..., max_length=255)
    trade_name: str | None = Field(None, max_length=255)
    tax_id: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    is_active: bool = True
    notes: str | None = None


class SupplierCreate(SupplierBase):
    """Schema for creating supplier"""

    contacts: list[SupplierContactCreate] = Field(default_factory=list)
    addresses: list[SupplierAddressCreate] = Field(default_factory=list)


class SupplierUpdate(BaseModel):
    """Schema for updating supplier"""

    code: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    trade_name: str | None = Field(None, max_length=255)
    tax_id: str | None = Field(None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class SupplierResponse(SupplierBase):
    """Schema for supplier response"""

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    contacts: list[SupplierContactResponse] = Field(default_factory=list)
    addresses: list[SupplierAddressResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SupplierList(BaseModel):
    """Schema for paginated supplier list"""

    items: list[SupplierResponse]
    total: int
    page: int = 1
    page_size: int = 100
