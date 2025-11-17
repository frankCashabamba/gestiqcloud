"""
CRM Pydantic Schemas
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.crm.domain.entities import (
    ActivityStatus,
    ActivityType,
    LeadSource,
    LeadStatus,
    OpportunityStage,
)


class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    company: str | None = Field(None, max_length=200)
    email: EmailStr
    phone: str | None = Field(None, max_length=50)
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.OTHER
    assigned_to: UUID | None = None
    score: int | None = Field(None, ge=0, le=100)
    notes: str | None = None
    custom_fields: dict | None = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    company: str | None = Field(None, max_length=200)
    email: EmailStr | None = None
    phone: str | None = None
    status: LeadStatus | None = None
    source: LeadSource | None = None
    assigned_to: UUID | None = None
    score: int | None = Field(None, ge=0, le=100)
    notes: str | None = None
    custom_fields: dict | None = None


class LeadOut(LeadBase):
    id: UUID
    tenant_id: UUID
    converted_at: datetime | None = None
    opportunity_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OpportunityBase(BaseModel):
    lead_id: UUID | None = None
    customer_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    value: float = Field(..., ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    probability: int = Field(default=50, ge=0, le=100)
    stage: OpportunityStage = OpportunityStage.QUALIFICATION
    expected_close_date: datetime | None = None
    assigned_to: UUID | None = None
    custom_fields: dict | None = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    lead_id: UUID | None = None
    customer_id: UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    value: float | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    probability: int | None = Field(None, ge=0, le=100)
    stage: OpportunityStage | None = None
    expected_close_date: datetime | None = None
    actual_close_date: datetime | None = None
    assigned_to: UUID | None = None
    lost_reason: str | None = None
    custom_fields: dict | None = None


class OpportunityOut(OpportunityBase):
    id: UUID
    tenant_id: UUID
    actual_close_date: datetime | None = None
    lost_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityBase(BaseModel):
    lead_id: UUID | None = None
    opportunity_id: UUID | None = None
    customer_id: UUID | None = None
    type: ActivityType = ActivityType.NOTE
    subject: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    status: ActivityStatus = ActivityStatus.PENDING
    due_date: datetime | None = None
    assigned_to: UUID | None = None


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    type: ActivityType | None = None
    subject: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None
    status: ActivityStatus | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None
    assigned_to: UUID | None = None


class ActivityOut(ActivityBase):
    id: UUID
    tenant_id: UUID
    created_by: UUID
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardMetrics(BaseModel):
    total_leads: int
    total_opportunities: int
    total_pipeline_value: float
    conversion_rate: float
    won_opportunities: int
    lost_opportunities: int
    leads_by_status: dict[str, int]
    opportunities_by_stage: dict[str, int]


class ConvertLeadRequest(BaseModel):
    create_opportunity: bool = True
    opportunity_title: str | None = None
    opportunity_value: float | None = None
