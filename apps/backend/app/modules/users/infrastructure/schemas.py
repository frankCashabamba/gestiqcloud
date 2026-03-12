from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyUserBase(BaseModel):
    first_name: str | None = Field(
        default=None,
    )
    last_name: str | None = Field(
        default=None,
    )
    email: str
    username: str | None = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CompanyUserCreate(CompanyUserBase):
    password: str = Field(min_length=8)
    active: bool = Field(default=True)
    is_company_admin: bool = Field(default=False)
    as_employee: bool = Field(default=False)
    employee_hire_date: date | None = None
    employee_department: str | None = None
    employee_job_title: str | None = None
    employee_salary_base: Decimal | None = None
    employee_payment_mode: str | None = None
    modules: list[UUID] = Field(default_factory=list)
    roles: list[UUID] = Field(default_factory=list)


class CompanyUserUpdate(BaseModel):
    first_name: str | None = Field(
        default=None,
    )
    last_name: str | None = Field(
        default=None,
    )
    email: str | None = None
    username: str | None = None
    password: str | None = Field(default=None, min_length=8)
    is_company_admin: bool | None = Field(default=None)
    active: bool | None = Field(default=None)
    as_employee: bool | None = Field(default=None)
    employee_hire_date: date | None = None
    employee_department: str | None = None
    employee_job_title: str | None = None
    employee_salary_base: Decimal | None = None
    employee_payment_mode: str | None = None
    modules: list[UUID] | None = Field(default=None)
    roles: list[UUID] | None = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CompanyUserOut(CompanyUserBase):
    id: UUID
    tenant_id: UUID
    is_company_admin: bool
    active: bool
    as_employee: bool = Field(default=False)
    employee_hire_date: date | None = None
    employee_department: str | None = None
    employee_job_title: str | None = None
    employee_salary_base: Decimal | None = None
    employee_payment_mode: str | None = None
    modules: list[UUID] = Field(default_factory=list)
    roles: list[UUID] = Field(default_factory=list)
    last_login_at: datetime | None = Field(
        default=None,
        validation_alias="last_login_at",
        serialization_alias="last_login_at",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ModuleOption(BaseModel):
    id: UUID
    name: str | None = None
    category: str | None = None
    icon: str | None = None


class CompanyRoleOption(BaseModel):
    id: UUID
    name: str
    description: str | None = None
