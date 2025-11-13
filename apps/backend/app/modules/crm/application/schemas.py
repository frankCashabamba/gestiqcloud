"""
CRM Pydantic Schemas
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID

from app.modules.crm.domain.entities import (
    LeadStatus, LeadSource, OpportunityStage, ActivityType, ActivityStatus
)


class LeadBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.OTHER
    assigned_to: Optional[UUID] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    custom_fields: Optional[dict] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    company: Optional[str] = Field(None, max_length=200)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[LeadStatus] = None
    source: Optional[LeadSource] = None
    assigned_to: Optional[UUID] = None
    score: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    custom_fields: Optional[dict] = None


class LeadOut(LeadBase):
    id: UUID
    tenant_id: UUID
    converted_at: Optional[datetime] = None
    opportunity_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OpportunityBase(BaseModel):
    lead_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    value: float = Field(..., ge=0)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    probability: int = Field(default=50, ge=0, le=100)
    stage: OpportunityStage = OpportunityStage.QUALIFICATION
    expected_close_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None
    custom_fields: Optional[dict] = None


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    lead_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    value: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    probability: Optional[int] = Field(None, ge=0, le=100)
    stage: Optional[OpportunityStage] = None
    expected_close_date: Optional[datetime] = None
    actual_close_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None
    lost_reason: Optional[str] = None
    custom_fields: Optional[dict] = None


class OpportunityOut(OpportunityBase):
    id: UUID
    tenant_id: UUID
    actual_close_date: Optional[datetime] = None
    lost_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ActivityBase(BaseModel):
    lead_id: Optional[UUID] = None
    opportunity_id: Optional[UUID] = None
    customer_id: Optional[UUID] = None
    type: ActivityType = ActivityType.NOTE
    subject: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    status: ActivityStatus = ActivityStatus.PENDING
    due_date: Optional[datetime] = None
    assigned_to: Optional[UUID] = None


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    type: Optional[ActivityType] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=300)
    description: Optional[str] = None
    status: Optional[ActivityStatus] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[UUID] = None


class ActivityOut(ActivityBase):
    id: UUID
    tenant_id: UUID
    created_by: UUID
    completed_at: Optional[datetime] = None
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
    opportunity_title: Optional[str] = None
    opportunity_value: Optional[float] = None
