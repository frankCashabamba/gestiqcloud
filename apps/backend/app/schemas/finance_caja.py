"""Cash management schemas."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


MovementType = Literal["INCOME", "EXPENSE", "ADJUSTMENT"]
CashCategory = Literal["SALE", "PURCHASE", "EXPENSE", "PAYROLL", "BANK", "CHANGE", "ADJUSTMENT", "OTHER"]


class CashMovementBase(BaseModel):
    movement_type: MovementType = Field(..., description="INCOME, EXPENSE, or ADJUSTMENT")
    category: CashCategory = Field(default="OTHER")
    amount: Decimal = Field(..., description="Movement amount")
    currency: str | None = Field(default=None, max_length=3)
    description: str = Field(..., max_length=255)
    notes: str | None = None
    date: dt.date = Field(default_factory=dt.date.today)
    ref_doc_type: str | None = None
    ref_doc_id: UUID | None = None
    cash_box_id: UUID | None = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            raise ValueError("amount must be greater than zero")
        return value


class CashMovementCreate(CashMovementBase):
    pass


class CashMovementResponse(CashMovementBase):
    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    closing_id: UUID | None = None
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class CashMovementList(BaseModel):
    items: list[CashMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BillBreakdown(BaseModel):
    bill_500: int = Field(default=0, ge=0)
    bill_200: int = Field(default=0, ge=0)
    bill_100: int = Field(default=0, ge=0)
    bill_50: int = Field(default=0, ge=0)
    bill_20: int = Field(default=0, ge=0)
    bill_10: int = Field(default=0, ge=0)
    bill_5: int = Field(default=0, ge=0)
    coin_2: int = Field(default=0, ge=0)
    coin_1: int = Field(default=0, ge=0)
    coin_050: int = Field(default=0, ge=0)
    coin_020: int = Field(default=0, ge=0)
    coin_010: int = Field(default=0, ge=0)
    coin_005: int = Field(default=0, ge=0)
    coin_002: int = Field(default=0, ge=0)
    coin_001: int = Field(default=0, ge=0)

    def calculate_total(self) -> Decimal:
        total = Decimal("0")
        total += self.bill_500 * Decimal("500")
        total += self.bill_200 * Decimal("200")
        total += self.bill_100 * Decimal("100")
        total += self.bill_50 * Decimal("50")
        total += self.bill_20 * Decimal("20")
        total += self.bill_10 * Decimal("10")
        total += self.bill_5 * Decimal("5")
        total += self.coin_2 * Decimal("2")
        total += self.coin_1 * Decimal("1")
        total += self.coin_050 * Decimal("0.50")
        total += self.coin_020 * Decimal("0.20")
        total += self.coin_010 * Decimal("0.10")
        total += self.coin_005 * Decimal("0.05")
        total += self.coin_002 * Decimal("0.02")
        total += self.coin_001 * Decimal("0.01")
        return total


class CashClosingBase(BaseModel):
    date: dt.date
    cash_box_id: UUID | None = None
    currency: str | None = Field(default=None, max_length=3)
    opening_balance: Decimal = Field(default=Decimal("0"))
    notes: str | None = None


class CashClosingCreate(CashClosingBase):
    total_income: Decimal = Field(default=Decimal("0"))
    total_expense: Decimal = Field(default=Decimal("0"))


class CashClosingClose(BaseModel):
    physical_balance: Decimal
    bill_breakdown: BillBreakdown | None = None
    notes: str | None = None


class CashClosingResponse(CashClosingBase):
    id: UUID
    tenant_id: UUID
    total_income: Decimal
    total_expense: Decimal
    theoretical_balance: Decimal
    physical_balance: Decimal
    difference: Decimal
    status: str
    is_balanced: bool
    bill_breakdown: dict[str, Any] | None = None
    opened_by: UUID | None = None
    opened_at: dt.datetime | None = None
    closed_by: UUID | None = None
    closed_at: dt.datetime | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class CashClosingList(BaseModel):
    items: list[CashClosingResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CashBalanceResponse(BaseModel):
    date: dt.date
    currency: str
    opening_balance: Decimal
    total_income_today: Decimal
    total_expense_today: Decimal
    current_balance: Decimal
    cash_box_id: UUID | None
    has_open_closing: bool


class CashStats(BaseModel):
    date_from: dt.date
    date_to: dt.date
    currency: str
    total_income: Decimal
    total_expense: Decimal
    net_balance: Decimal
    income_by_category: dict[str, Decimal] = Field(default_factory=dict)
    expense_by_category: dict[str, Decimal] = Field(default_factory=dict)
    avg_income_per_day: Decimal
    avg_expense_per_day: Decimal
    total_closings: int
    balanced_closings: int
    total_differences: Decimal
    total_movements: int
    total_income_count: int
    total_expense_count: int
