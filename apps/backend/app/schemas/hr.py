"""HR schemas."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

EmployeeStatus = Literal["active", "inactive", "suspended"]
VacationStatus = Literal["pending", "approved", "rejected", "cancelled"]
VacationType = Literal["annual", "sick", "personal", "unpaid"]
IdentificationType = Literal["dni", "ruc", "cedula", "passport"]


class EmployeeBase(BaseModel):
    name: str = Field(..., max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identification: str | None = Field(None, max_length=20)
    identification_type: IdentificationType | None = None
    birth_date: date | None = None
    hire_date: date = Field(default_factory=date.today)
    termination_date: date | None = None
    position: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    salary: float | None = Field(None, ge=0)
    status: EmployeeStatus = Field(default="active")
    address: str | None = Field(None, max_length=255)
    notes: str | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20, pattern=r"^\+?[\d\s\-()]+$")
    identification: str | None = Field(None, max_length=20)
    identification_type: IdentificationType | None = None
    birth_date: date | None = None
    hire_date: date | None = None
    termination_date: date | None = None
    position: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    salary: float | None = Field(None, ge=0)
    status: EmployeeStatus | None = None
    address: str | None = Field(None, max_length=255)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class EmployeeResponse(EmployeeBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeList(BaseModel):
    items: list[EmployeeResponse]
    total: int
    page: int = 1
    page_size: int = 100


class VacationBase(BaseModel):
    employee_id: UUID = Field(..., description="Employee ID")
    start_date: date = Field(...)
    end_date: date = Field(...)
    total_days: int = Field(..., ge=1)
    type: VacationType = Field(default="annual")
    status: VacationStatus = Field(default="pending")
    reason: str | None = Field(None, max_length=500)
    approved_by: UUID | None = None
    approval_date: datetime | None = None
    notes: str | None = None


class VacationCreate(VacationBase):
    pass


class VacationUpdate(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    total_days: int | None = Field(None, ge=1)
    type: VacationType | None = None
    status: VacationStatus | None = None
    reason: str | None = Field(None, max_length=500)
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class VacationResponse(VacationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VacationList(BaseModel):
    items: list[VacationResponse]
    total: int
    page: int = 1
    page_size: int = 100
