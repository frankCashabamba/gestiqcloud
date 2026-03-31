"""Incidents and alerts router."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.access_guard import with_access_claims
from app.core.authz import require_scope
from app.models.ai.incident import Incident, NotificationChannel, NotificationLog, StockAlert
from app.modules.ai_agent.analyzer import (
    analyze_incident_with_ia,
    auto_resolve_incident,
    suggest_fix,
)
from app.schemas.incidents import (
    IncidentAnalysisRequest,
    IncidentAnalysisResponse,
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationLogResponse,
    StockAlertCreate,
    StockAlertResponse,
)

router = APIRouter(
    prefix="/incidents",
    tags=["Incidents & IA"],
    dependencies=[Depends(with_access_claims), Depends(require_scope("admin"))],
)


def _is_superadmin_request(request: Request) -> bool:
    claims = getattr(request.state, "access_claims", None) or {}
    return bool(
        isinstance(claims, dict)
        and (
            claims.get("is_superadmin")
            or claims.get("kind") == "admin"
            or claims.get("scope") == "admin"
        )
    )


def _coerce_uuid(value: str | UUID | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="invalid_uuid")


def _split_csv_values(*values: str | None) -> list[str]:
    items: list[str] = []
    for raw in values:
        if not raw:
            continue
        for part in str(raw).split(","):
            token = part.strip()
            if token:
                items.append(token)
    return items


def _incident_query_for_request(
    db: Session,
    request: Request,
    *,
    tenant_id: str | None = None,
):
    query = db.query(Incident)
    if tenant_id:
        query = query.filter(Incident.tenant_id == _coerce_uuid(tenant_id))
    elif not _is_superadmin_request(request):
        claims = getattr(request.state, "access_claims", None) or {}
        claim_tenant_id = claims.get("tenant_id") if isinstance(claims, dict) else None
        tenant_uuid = _coerce_uuid(claim_tenant_id)
        if not tenant_uuid:
            raise HTTPException(status_code=403, detail="missing_tenant")
        query = query.filter(Incident.tenant_id == tenant_uuid)
    return query


def _tenant_uuid_for_request(request: Request, tenant_id: str | None = None) -> UUID:
    explicit_tenant_id = _coerce_uuid(tenant_id)
    if explicit_tenant_id:
        return explicit_tenant_id

    claims = getattr(request.state, "access_claims", None) or {}
    claim_tenant_id = claims.get("tenant_id") if isinstance(claims, dict) else None
    tenant_uuid = _coerce_uuid(claim_tenant_id)
    if tenant_uuid:
        return tenant_uuid

    raise HTTPException(status_code=422, detail="tenant_id_required")


def _get_incident_for_request(
    db: Session,
    request: Request,
    incident_id: UUID,
):
    incident = _incident_query_for_request(db, request).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


# ============================================================================
# INCIDENTS CRUD
# ============================================================================


@router.get("/", response_model=list[IncidentResponse])
async def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    type_: str | None = None,
    type: str | None = None,
    severity: str | None = None,
    status_: str | None = None,
    status: str | None = None,
    estado: str | None = None,
    tenant_id: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """List tenant incidents with filters"""
    query = _incident_query_for_request(db, request, tenant_id=tenant_id)

    type_values = _split_csv_values(type_, type)
    if type_values:
        query = query.filter(Incident.type.in_(type_values))

    severity_values = _split_csv_values(severity)
    if severity_values:
        query = query.filter(Incident.severity.in_(severity_values))

    status_values = _split_csv_values(status_, status, estado)
    if status_values:
        query = query.filter(Incident.status.in_(status_values))

    incidents = query.order_by(desc(Incident.created_at)).offset(skip).limit(limit).all()
    return incidents


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_data: IncidentCreate,
    request: Request,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Create a new incident (manual or auto-detected)"""
    tenant_uuid = _tenant_uuid_for_request(request, tenant_id)

    new_incident = Incident(
        tenant_id=tenant_uuid,
        type=incident_data.type,
        severity=incident_data.severity,
        title=incident_data.title,
        description=incident_data.description,
        stack_trace=incident_data.stack_trace,
        context=incident_data.context,
        auto_detected=False,
    )

    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return new_incident


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get incident details"""
    return _get_incident_for_request(db, request, incident_id)


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    incident_update: IncidentUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update an incident"""
    incident = _get_incident_for_request(db, request, incident_id)

    update_data = incident_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    if incident_update.status == "resolved" and not incident.resolved_at:
        incident.resolved_at = datetime.now(UTC)

    db.commit()
    db.refresh(incident)

    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Delete an incident"""
    incident = _get_incident_for_request(db, request, incident_id)

    db.delete(incident)
    db.commit()

    return None


# ============================================================================
# AI ANALYSIS
# ============================================================================


@router.post("/{incident_id}/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incident(
    incident_id: UUID,
    analysis_request: IncidentAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Analyze incident with AI and suggest solutions"""
    _get_incident_for_request(db, request, incident_id)

    try:
        result = await analyze_incident_with_ia(
            incident_id=incident_id,
            use_gpt4=analysis_request.use_gpt4,
            include_code_suggestions=analysis_request.include_code_suggestions,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis error: {str(e)}")


@router.post("/{incident_id}/suggest-fix")
async def get_fix_suggestion(
    incident_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get code suggestion to resolve incident"""
    _get_incident_for_request(db, request, incident_id)

    try:
        suggestion = await suggest_fix(incident_id, db)
        return suggestion
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating suggestion: {str(e)}")


@router.post("/{incident_id}/resolve")
@router.post("/{incident_id}/auto-resolve")
async def resolve_incident(
    incident_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Attempt to auto-resolve incident with AI"""
    _get_incident_for_request(db, request, incident_id)

    try:
        result = await auto_resolve_incident(incident_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auto-resolve error: {str(e)}")


# ============================================================================
# STOCK ALERTS
# ============================================================================


@router.get("/stock-alerts/", response_model=list[StockAlertResponse])
async def list_stock_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    alert_type: str | None = None,
    status: str | None = None,
    estado: str | None = None,
    tenant_id: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    """List tenant stock alerts"""
    query = db.query(StockAlert)
    tenant_uuid = _coerce_uuid(tenant_id)
    if tenant_uuid:
        query = query.filter(StockAlert.tenant_id == tenant_uuid)
    elif not _is_superadmin_request(request):
        query = query.filter(StockAlert.tenant_id == _tenant_uuid_for_request(request))

    if alert_type:
        query = query.filter(StockAlert.alert_type == alert_type)
    status_values = _split_csv_values(status, estado)
    if status_values:
        query = query.filter(StockAlert.status.in_(status_values))

    alerts = query.order_by(desc(StockAlert.created_at)).offset(skip).limit(limit).all()
    return alerts


@router.post(
    "/stock-alerts/",
    response_model=StockAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_alert(
    alert_data: StockAlertCreate,
    request: Request,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Create a stock alert"""
    tenant_uuid = _tenant_uuid_for_request(request, tenant_id)

    new_alert = StockAlert(
        tenant_id=tenant_uuid,
        product_id=alert_data.product_id,
        warehouse_id=alert_data.warehouse_id,
        alert_type=alert_data.alert_type,
        current_qty=alert_data.current_qty,
        threshold_qty=alert_data.threshold_qty,
        threshold_config=alert_data.threshold_config,
    )

    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)

    return new_alert


@router.post("/stock-alerts/{alert_id}/notify")
async def notify_stock_alert(
    alert_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Send stock alert notification"""
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not _is_superadmin_request(request):
        request_tenant_id = _tenant_uuid_for_request(request)
        if alert.tenant_id != request_tenant_id:
            raise HTTPException(status_code=404, detail="Alert not found")

    channels = (
        db.query(NotificationChannel)
        .filter(
            and_(
                NotificationChannel.tenant_id == alert.tenant_id,
                NotificationChannel.is_active,
            )
        )
        .order_by(desc(NotificationChannel.priority))
        .all()
    )

    if not channels:
        raise HTTPException(status_code=400, detail="No notification channels configured")

    from app.modules.ai_agent.notifier import send_notification

    try:
        await send_notification(channel=channels[0], alert=alert, db=db)

        alert.notified_at = datetime.now(UTC)
        db.commit()

        return {"message": "Notification sent", "channel": channels[0].channel_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending notification: {str(e)}")


@router.post("/stock-alerts/{alert_id}/resolve")
async def resolve_stock_alert(
    alert_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Mark stock alert as resolved"""
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if not _is_superadmin_request(request):
        request_tenant_id = _tenant_uuid_for_request(request)
        if alert.tenant_id != request_tenant_id:
            raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "resolved"
    alert.resolved_at = datetime.now(UTC)
    db.commit()

    return {"message": "Alert resolved", "alert_id": str(alert_id)}


# ============================================================================
# NOTIFICATION CHANNELS
# ============================================================================


@router.get("/notifications/channels", response_model=list[NotificationChannelResponse])
async def list_notification_channels(
    request: Request,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List tenant notification channels"""
    tenant_uuid = _tenant_uuid_for_request(request, tenant_id)

    channels = (
        db.query(NotificationChannel)
        .filter(NotificationChannel.tenant_id == tenant_uuid)
        .order_by(desc(NotificationChannel.priority))
        .all()
    )

    return channels


@router.post(
    "/notifications/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_channel(
    channel_data: NotificationChannelCreate,
    request: Request,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Create a notification channel"""
    tenant_uuid = _tenant_uuid_for_request(request, tenant_id)

    new_channel = NotificationChannel(
        tenant_id=tenant_uuid,
        channel_type=getattr(channel_data, "channel_type", None)
        or getattr(channel_data, "tipo", None),
        name=channel_data.name,
        config=channel_data.config,
        is_active=(
            getattr(channel_data, "is_active", None)
            if getattr(channel_data, "is_active", None) is not None
            else getattr(channel_data, "active", True)
        ),
    )

    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    return new_channel


@router.put("/notifications/channels/{channel_id}", response_model=NotificationChannelResponse)
async def update_notification_channel(
    channel_id: UUID,
    channel_update: NotificationChannelUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Update a notification channel"""
    channel = db.query(NotificationChannel).filter(NotificationChannel.id == channel_id).first()

    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not _is_superadmin_request(request):
        request_tenant_id = _tenant_uuid_for_request(request)
        if channel.tenant_id != request_tenant_id:
            raise HTTPException(status_code=404, detail="Channel not found")

    update_data = channel_update.model_dump(exclude_unset=True)
    # Map schema field names to ORM column names
    _field_map = {"active": "is_active", "tipo": "channel_type"}
    for field, value in update_data.items():
        setattr(channel, _field_map.get(field, field), value)

    db.commit()
    db.refresh(channel)

    return channel


@router.get("/notifications/log", response_model=list[NotificationLogResponse])
async def get_notification_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    request: Request = None,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Get notification history"""
    tenant_uuid = _coerce_uuid(tenant_id)
    if not tenant_uuid:
        tenant_uuid = _tenant_uuid_for_request(request)

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.tenant_id == tenant_uuid)
        .order_by(desc(NotificationLog.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return logs
