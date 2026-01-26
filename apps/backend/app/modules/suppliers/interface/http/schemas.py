from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, Field, StringConstraints

ContactType = Literal[
    "billing",
    "delivery",
    "administration",
    "commercial",
    "support",
]

AddressType = Literal[
    "billing",
    "delivery",
    "administration",
    "other",
]

# Type aliases for constrained strings
StrStripped = Annotated[str, StringConstraints(strip_whitespace=True)]
StrNIF = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]
StrCountry = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=3)]
StrLang = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8)]
StrCurrency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3)]
StrIBAN = Annotated[str, StringConstraints(strip_whitespace=True, max_length=34)]


class SupplierContactIn(BaseModel):
    type: ContactType
    name: str | None = None
    email: EmailStr | None = None
    phone: StrStripped | None = None
    notes: str | None = Field(default=None, max_length=255)


class SupplierAddressIn(BaseModel):
    type: AddressType
    line1: str
    line2: str | None = None
    city: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: StrCountry | None = None
    notes: str | None = Field(default=None, max_length=255)


class SupplierBase(BaseModel):
    name: str
    trade_name: str | None = None
    tax_id: StrNIF | None = None
    country: StrCountry | None = None
    language: StrLang | None = None

    tax_type: str | None = None
    tax_withholding: float | None = Field(default=None, ge=0, le=100)
    tax_exempt: bool = False
    special_regime: str | None = None

    payment_terms: str | None = None
    payment_days: int | None = Field(default=None, ge=0, le=365)
    early_payment_discount: float | None = Field(default=None, ge=0, le=100)
    currency: StrCurrency | None = None
    payment_method: str | None = None
    iban: StrIBAN | None = None
    iban_confirmation: str | None = Field(default=None, exclude=True)

    contacts: list[SupplierContactIn] = Field(default_factory=list)
    addresses: list[SupplierAddressIn] = Field(default_factory=list)


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    pass


class SupplierContactOut(SupplierContactIn):
    id: UUID


class SupplierAddressOut(SupplierAddressIn):
    id: UUID


class SupplierOut(SupplierBase):
    id: UUID
    tenant_id: UUID
    iban_updated_by: str | None = None
    iban_updated_at: datetime | None = None
    contacts: list[SupplierContactOut] = Field(default_factory=list)
    addresses: list[SupplierAddressOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SupplierListOut(BaseModel):
    id: UUID
    name: str
    trade_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
