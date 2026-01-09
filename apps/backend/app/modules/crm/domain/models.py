"""
CRM Database Models
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.modules.crm.domain.entities import (
    ActivityStatus,
    ActivityType,
    LeadSource,
    LeadStatus,
    OpportunityStage,
)

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    """Return the values for a SQLAlchemy enum type."""
    return [member.value for member in enum_cls]


class Lead(Base):
    __tablename__ = "crm_leads"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="leadstatus", values_callable=_enum_values),
        nullable=False,
        default=LeadStatus.NEW,
        index=True,
    )
    source: Mapped[LeadSource] = mapped_column(
        SAEnum(LeadSource, name="leadsource", values_callable=_enum_values),
        nullable=False,
        default=LeadSource.OTHER,
    )

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=True
    )

    score: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)

    converted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    assigned_user = relationship("CompanyUser", foreign_keys=[assigned_to])


class Opportunity(Base):
    __tablename__ = "crm_opportunities"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    probability: Mapped[int] = mapped_column(nullable=False, default=50)

    stage: Mapped[OpportunityStage] = mapped_column(
        SAEnum(
            OpportunityStage,
            name="opportunitystage",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=OpportunityStage.QUALIFICATION,
        index=True,
    )

    expected_close_date: Mapped[datetime | None] = mapped_column(nullable=True)
    actual_close_date: Mapped[datetime | None] = mapped_column(nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=True
    )
    lost_reason: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    customer = relationship("Client", foreign_keys=[customer_id])
    assigned_user = relationship("CompanyUser", foreign_keys=[assigned_to])


class Activity(Base):
    __tablename__ = "crm_activities"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )

    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("crm_leads.id"), nullable=True, index=True
    )
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("crm_opportunities.id"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True
    )

    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    type: Mapped[ActivityType] = mapped_column(
        SAEnum(ActivityType, name="activitytype", values_callable=_enum_values),
        nullable=False,
        default=ActivityType.NOTE,
    )
    status: Mapped[ActivityStatus] = mapped_column(
        SAEnum(ActivityStatus, name="activitystatus", values_callable=_enum_values),
        nullable=False,
        default=ActivityStatus.PENDING,
    )

    due_date: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("company_users.id"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    lead = relationship("Lead", foreign_keys=[lead_id])
    opportunity = relationship("Opportunity", foreign_keys=[opportunity_id])
    customer = relationship("Client", foreign_keys=[customer_id])
    assigned_user = relationship("CompanyUser", foreign_keys=[assigned_to])
    creator = relationship("CompanyUser", foreign_keys=[created_by])
