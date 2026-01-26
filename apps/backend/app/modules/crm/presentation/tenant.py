"""
CRM Tenant API Endpoints
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.db.rls import ensure_rls
from app.modules.crm.application.schemas import (
    ActivityCreate,
    ActivityOut,
    ActivityUpdate,
    ConvertLeadRequest,
    DashboardMetrics,
    LeadCreate,
    LeadOut,
    LeadUpdate,
    OpportunityCreate,
    OpportunityOut,
    OpportunityUpdate,
)
from app.modules.crm.application.services import CRMService
from app.modules.crm.domain.entities import ActivityStatus, LeadStatus, OpportunityStage

router = APIRouter(
    prefix="/crm",
    tags=["CRM"],
    dependencies=[
        Depends(with_access_claims),
        Depends(require_scope("tenant")),
        Depends(ensure_rls),
    ],
)


def _get_tenant_id(request: Request) -> UUID:
    raw = getattr(request.state, "access_claims", {}).get("tenant_id")
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="tenant_id inválido")


def _get_user_id(request: Request) -> UUID:
    claims = request.state.access_claims
    user_id = claims.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Usuario no autenticado")
    return UUID(str(user_id))


@router.get("/dashboard", response_model=DashboardMetrics)
def get_dashboard(request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)
    return service.get_dashboard(tenant_id)


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    request: Request,
    db: Session = Depends(get_db),
    status: LeadStatus | None = None,
    assigned_to: str | None = Query(None),
    source: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    assigned_uuid = UUID(assigned_to) if assigned_to else None

    return service.list_leads(
        tenant_id=tenant_id,
        status=status,
        assigned_to=assigned_uuid,
        source=source,
        limit=limit,
        offset=offset,
    )


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    lead = service.get_lead(tenant_id, UUID(lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    return lead


@router.post("/leads", response_model=LeadOut, status_code=201)
def create_lead(data: LeadCreate, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    return service.create_lead(tenant_id, data)


@router.put("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: str, data: LeadUpdate, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    lead = service.update_lead(tenant_id, UUID(lead_id), data)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")

    return lead


@router.delete("/leads/{lead_id}", status_code=204)
def delete_lead(lead_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    if not service.delete_lead(tenant_id, UUID(lead_id)):
        raise HTTPException(status_code=404, detail="Lead no encontrado")


@router.post("/leads/{lead_id}/convert", response_model=OpportunityOut)
def convert_lead(
    lead_id: str, payload: ConvertLeadRequest, request: Request, db: Session = Depends(get_db)
):
    tenant_id = _get_tenant_id(request)
    service = CRMService(db)

    try:
        opportunity = service.convert_lead(
            tenant_id=tenant_id,
            lead_id=UUID(lead_id),
            create_opportunity=payload.create_opportunity,
            opportunity_data=(
                {
                    "title": payload.opportunity_title,
                    "value": payload.opportunity_value,
                }
                if payload.create_opportunity
                else None
            ),
        )
    except ValueError as e:
        if str(e) == "currency_not_configured":
            raise HTTPException(status_code=400, detail="currency_not_configured")
        raise

    if not opportunity:
        raise HTTPException(status_code=404, detail="Lead no encontrado o ya convertido")

    return opportunity


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(
    request: Request,
    db: Session = Depends(get_db),
    stage: OpportunityStage | None = None,
    assigned_to: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    assigned_uuid = UUID(assigned_to) if assigned_to else None

    return service.list_opportunities(
        tenant_id=tenant_id, stage=stage, assigned_to=assigned_uuid, limit=limit, offset=offset
    )


@router.get("/opportunities/{opp_id}", response_model=OpportunityOut)
def get_opportunity(opp_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    opp = service.get_opportunity(tenant_id, UUID(opp_id))
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    return opp


@router.post("/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(data: OpportunityCreate, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    return service.create_opportunity(tenant_id, data)


@router.put("/opportunities/{opp_id}", response_model=OpportunityOut)
def update_opportunity(
    opp_id: str, data: OpportunityUpdate, request: Request, db: Session = Depends(get_db)
):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    opp = service.update_opportunity(tenant_id, UUID(opp_id), data)
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    return opp


@router.delete("/opportunities/{opp_id}", status_code=204)
def delete_opportunity(opp_id: str, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    if not service.delete_opportunity(tenant_id, UUID(opp_id)):
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    request: Request,
    db: Session = Depends(get_db),
    lead_id: str | None = Query(None),
    opportunity_id: str | None = Query(None),
    status: ActivityStatus | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    lead_uuid = UUID(lead_id) if lead_id else None
    opp_uuid = UUID(opportunity_id) if opportunity_id else None

    return service.list_activities(
        tenant_id=tenant_id,
        lead_id=lead_uuid,
        opportunity_id=opp_uuid,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/activities", response_model=ActivityOut, status_code=201)
def create_activity(data: ActivityCreate, request: Request, db: Session = Depends(get_db)):
    tenant_id = _get_tenant_id(request, db)
    user_id = _get_user_id(request)
    service = CRMService(db)

    return service.create_activity(tenant_id, user_id, data)


@router.put("/activities/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: str, data: ActivityUpdate, request: Request, db: Session = Depends(get_db)
):
    tenant_id = _get_tenant_id(request, db)
    service = CRMService(db)

    activity = service.update_activity(tenant_id, UUID(activity_id), data)
    if not activity:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")

    return activity
