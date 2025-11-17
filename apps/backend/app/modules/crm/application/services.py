"""
CRM Application Services
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.crm.application.schemas import (
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    DashboardMetrics,
    LeadCreate,
    LeadOut,
    LeadUpdate,
    OpportunityCreate,
    OpportunityOut,
    OpportunityUpdate,
)
from app.modules.crm.domain.entities import ActivityStatus, LeadStatus, OpportunityStage
from app.modules.crm.domain.models import Activity, Lead, Opportunity


class CRMService:
    def __init__(self, db: Session):
        self.db = db

    def list_leads(
        self,
        tenant_id: UUID,
        status: LeadStatus | None = None,
        assigned_to: UUID | None = None,
        source: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LeadOut]:
        query = self.db.query(Lead).filter(Lead.tenant_id == tenant_id)

        if status:
            query = query.filter(Lead.status == status)
        if assigned_to:
            query = query.filter(Lead.assigned_to == assigned_to)
        if source:
            query = query.filter(Lead.source == source)

        leads = query.order_by(Lead.created_at.desc()).offset(offset).limit(limit).all()
        return [LeadOut.model_validate(lead) for lead in leads]

    def get_lead(self, tenant_id: UUID, lead_id: UUID) -> LeadOut | None:
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
        return LeadOut.model_validate(lead) if lead else None

    def create_lead(self, tenant_id: UUID, data: LeadCreate) -> LeadOut:
        lead = Lead(tenant_id=tenant_id, **data.model_dump())
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return LeadOut.model_validate(lead)

    def update_lead(self, tenant_id: UUID, lead_id: UUID, data: LeadUpdate) -> LeadOut | None:
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()

        if not lead:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(lead, field, value)

        lead.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(lead)
        return LeadOut.model_validate(lead)

    def delete_lead(self, tenant_id: UUID, lead_id: UUID) -> bool:
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()

        if not lead:
            return False

        self.db.delete(lead)
        self.db.commit()
        return True

    def convert_lead(
        self,
        tenant_id: UUID,
        lead_id: UUID,
        create_opportunity: bool = True,
        opportunity_data: dict | None = None,
    ) -> OpportunityOut | None:
        lead = self.db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()

        if not lead or lead.status == LeadStatus.WON:
            return None

        lead.status = LeadStatus.WON
        lead.converted_at = datetime.utcnow()

        opportunity = None
        if create_opportunity:
            opp_data = opportunity_data or {}
            opportunity = Opportunity(
                tenant_id=tenant_id,
                lead_id=lead_id,
                title=opp_data.get("title") or f"Oportunidad de {lead.name}",
                value=opp_data.get("value", 0),
                currency=opp_data.get("currency", "EUR"),
                probability=opp_data.get("probability", 50),
                stage=OpportunityStage.QUALIFICATION,
                assigned_to=lead.assigned_to,
            )
            self.db.add(opportunity)
            self.db.flush()

            lead.opportunity_id = opportunity.id

        self.db.commit()

        if opportunity:
            self.db.refresh(opportunity)
            return OpportunityOut.model_validate(opportunity)
        return None

    def list_opportunities(
        self,
        tenant_id: UUID,
        stage: OpportunityStage | None = None,
        assigned_to: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[OpportunityOut]:
        query = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id)

        if stage:
            query = query.filter(Opportunity.stage == stage)
        if assigned_to:
            query = query.filter(Opportunity.assigned_to == assigned_to)

        opps = query.order_by(Opportunity.created_at.desc()).offset(offset).limit(limit).all()
        return [OpportunityOut.model_validate(opp) for opp in opps]

    def get_opportunity(self, tenant_id: UUID, opp_id: UUID) -> OpportunityOut | None:
        opp = (
            self.db.query(Opportunity)
            .filter(Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id)
            .first()
        )
        return OpportunityOut.model_validate(opp) if opp else None

    def create_opportunity(self, tenant_id: UUID, data: OpportunityCreate) -> OpportunityOut:
        opp = Opportunity(tenant_id=tenant_id, **data.model_dump())
        self.db.add(opp)
        self.db.commit()
        self.db.refresh(opp)
        return OpportunityOut.model_validate(opp)

    def update_opportunity(
        self, tenant_id: UUID, opp_id: UUID, data: OpportunityUpdate
    ) -> OpportunityOut | None:
        opp = (
            self.db.query(Opportunity)
            .filter(Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id)
            .first()
        )

        if not opp:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(opp, field, value)

        opp.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(opp)
        return OpportunityOut.model_validate(opp)

    def delete_opportunity(self, tenant_id: UUID, opp_id: UUID) -> bool:
        opp = (
            self.db.query(Opportunity)
            .filter(Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id)
            .first()
        )

        if not opp:
            return False

        self.db.delete(opp)
        self.db.commit()
        return True

    def get_dashboard(self, tenant_id: UUID) -> DashboardMetrics:
        total_leads = (
            self.db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id).scalar() or 0
        )

        total_opportunities = (
            self.db.query(func.count(Opportunity.id))
            .filter(Opportunity.tenant_id == tenant_id)
            .scalar()
            or 0
        )

        total_pipeline_value = (
            self.db.query(func.coalesce(func.sum(Opportunity.value), 0))
            .filter(
                Opportunity.tenant_id == tenant_id,
                Opportunity.stage.not_in(
                    [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]
                ),
            )
            .scalar()
            or 0.0
        )

        won_opportunities = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                Opportunity.tenant_id == tenant_id, Opportunity.stage == OpportunityStage.CLOSED_WON
            )
            .scalar()
            or 0
        )

        lost_opportunities = (
            self.db.query(func.count(Opportunity.id))
            .filter(
                Opportunity.tenant_id == tenant_id,
                Opportunity.stage == OpportunityStage.CLOSED_LOST,
            )
            .scalar()
            or 0
        )

        total_closed = won_opportunities + lost_opportunities
        conversion_rate = (won_opportunities / total_closed * 100) if total_closed > 0 else 0.0

        leads_by_status = {}
        for status in LeadStatus:
            count = (
                self.db.query(func.count(Lead.id))
                .filter(Lead.tenant_id == tenant_id, Lead.status == status)
                .scalar()
                or 0
            )
            leads_by_status[status.value] = count

        opportunities_by_stage = {}
        for stage in OpportunityStage:
            count = (
                self.db.query(func.count(Opportunity.id))
                .filter(Opportunity.tenant_id == tenant_id, Opportunity.stage == stage)
                .scalar()
                or 0
            )
            opportunities_by_stage[stage.value] = count

        return DashboardMetrics(
            total_leads=total_leads,
            total_opportunities=total_opportunities,
            total_pipeline_value=float(total_pipeline_value),
            conversion_rate=float(conversion_rate),
            won_opportunities=won_opportunities,
            lost_opportunities=lost_opportunities,
            leads_by_status=leads_by_status,
            opportunities_by_stage=opportunities_by_stage,
        )

    def list_activities(
        self,
        tenant_id: UUID,
        lead_id: UUID | None = None,
        opportunity_id: UUID | None = None,
        status: ActivityStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ActivityOut]:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id)

        if lead_id:
            query = query.filter(Activity.lead_id == lead_id)
        if opportunity_id:
            query = query.filter(Activity.opportunity_id == opportunity_id)
        if status:
            query = query.filter(Activity.status == status)

        activities = query.order_by(Activity.created_at.desc()).offset(offset).limit(limit).all()
        return [ActivityOut.model_validate(act) for act in activities]

    def create_activity(self, tenant_id: UUID, user_id: UUID, data: ActivityCreate) -> ActivityOut:
        activity = Activity(tenant_id=tenant_id, created_by=user_id, **data.model_dump())
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return ActivityOut.model_validate(activity)

    def update_activity(
        self, tenant_id: UUID, activity_id: UUID, data: ActivityUpdate
    ) -> ActivityOut | None:
        activity = (
            self.db.query(Activity)
            .filter(Activity.id == activity_id, Activity.tenant_id == tenant_id)
            .first()
        )

        if not activity:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(activity, field, value)

        activity.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(activity)
        return ActivityOut.model_validate(activity)
