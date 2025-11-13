from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.ai.incident import (
    Incident,
    StockAlert,
    NotificationChannel,
    NotificationLog,
)
from app.schemas.incidents import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentAnalysisRequest,
    IncidentAnalysisResponse,
    StockAlertCreate,
    StockAlertResponse,
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationChannelResponse,
    NotificationLogResponse,
)
from app.modules.ai_agent.analyzer import (
    analyze_incident_with_ia,
    auto_resolve_incident,
    suggest_fix,
)

router = APIRouter(prefix="/incidents", tags=["Incidents & IA"])


# ============================================================================
# INCIDENTS CRUD
# ============================================================================


@router.get("/", response_model=List[IncidentResponse])
async def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tipo: Optional[str] = None,
    severidad: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Lista incidencias del tenant con filtros"""
    tenant_id = current_user["tenant_id"]

    query = db.query(Incident).filter(Incident.tenant_id == tenant_id)

    if tipo:
        query = query.filter(Incident.tipo == tipo)
    if severidad:
        query = query.filter(Incident.severidad == severidad)
    if estado:
        query = query.filter(Incident.estado == estado)

    incidents = (
        query.order_by(desc(Incident.created_at)).offset(skip).limit(limit).all()
    )
    return incidents


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_data: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Crea una nueva incidencia (manual o auto-detectada)"""
    tenant_id = current_user["tenant_id"]

    new_incident = Incident(
        tenant_id=tenant_id,
        tipo=incident_data.tipo,
        severidad=incident_data.severidad,
        titulo=incident_data.titulo,
        descripcion=incident_data.description,
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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene detalles de una incidencia"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    return incident


@router.put("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    incident_update: IncidentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualiza una incidencia"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    update_data = incident_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(incident, field, value)

    if incident_update.estado == "resolved" and not incident.resolved_at:
        from datetime import datetime

        incident.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(incident)

    return incident


@router.delete("/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Elimina una incidencia"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    db.delete(incident)
    db.commit()

    return None


# ============================================================================
# IA ANALYSIS
# ============================================================================


@router.post("/{incident_id}/analyze", response_model=IncidentAnalysisResponse)
async def analyze_incident(
    incident_id: UUID,
    analysis_request: IncidentAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Analiza incidencia con IA y sugiere soluciones"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    try:
        result = await analyze_incident_with_ia(
            incident_id=incident_id,
            use_gpt4=analysis_request.use_gpt4,
            include_code_suggestions=analysis_request.include_code_suggestions,
            db=db,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en análisis IA: {str(e)}")


@router.post("/{incident_id}/suggest-fix")
async def get_fix_suggestion(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene sugerencia de código para resolver incidencia"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    try:
        suggestion = await suggest_fix(incident_id, db)
        return suggestion
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generando sugerencia: {str(e)}"
        )


@router.post("/{incident_id}/resolve")
async def resolve_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Intenta auto-resolver incidencia con IA"""
    tenant_id = current_user["tenant_id"]

    incident = (
        db.query(Incident)
        .filter(and_(Incident.id == incident_id, Incident.tenant_id == tenant_id))
        .first()
    )

    if not incident:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")

    try:
        result = await auto_resolve_incident(incident_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error auto-resolviendo: {str(e)}")


# ============================================================================
# STOCK ALERTS
# ============================================================================


@router.get("/stock-alerts/", response_model=List[StockAlertResponse])
async def list_stock_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    alert_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Lista alertas de stock del tenant"""
    tenant_id = current_user["tenant_id"]

    query = db.query(StockAlert).filter(StockAlert.tenant_id == tenant_id)

    if alert_type:
        query = query.filter(StockAlert.alert_type == alert_type)
    if status:
        query = query.filter(StockAlert.status == status)

    alerts = query.order_by(desc(StockAlert.created_at)).offset(skip).limit(limit).all()
    return alerts


@router.post(
    "/stock-alerts/",
    response_model=StockAlertResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_alert(
    alert_data: StockAlertCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Crea una alerta de stock"""
    tenant_id = current_user["tenant_id"]

    new_alert = StockAlert(
        tenant_id=tenant_id,
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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Envía notificación de alerta de stock"""
    tenant_id = current_user["tenant_id"]

    alert = (
        db.query(StockAlert)
        .filter(and_(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id))
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    # Obtener canales activos del tenant
    channels = (
        db.query(NotificationChannel)
        .filter(
            and_(
                NotificationChannel.tenant_id == tenant_id,
                NotificationChannel.is_active,
            )
        )
        .order_by(desc(NotificationChannel.priority))
        .all()
    )

    if not channels:
        raise HTTPException(
            status_code=400, detail="No hay canales de notificación configurados"
        )

    # Enviar notificación por el canal de mayor prioridad
    from app.modules.ai_agent.notifier import send_notification
    from datetime import datetime

    try:
        await send_notification(channel=channels[0], alert=alert, db=db)

        alert.notified_at = datetime.utcnow()
        db.commit()

        return {"message": "Notificación enviada", "channel": channels[0].tipo}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error enviando notificación: {str(e)}"
        )


@router.post("/stock-alerts/{alert_id}/resolve")
async def resolve_stock_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Marca alerta de stock como resuelta"""
    tenant_id = current_user["tenant_id"]

    alert = (
        db.query(StockAlert)
        .filter(and_(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id))
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    from datetime import datetime

    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": "Alerta resuelta", "alert_id": str(alert_id)}


# ============================================================================
# NOTIFICATION CHANNELS
# ============================================================================


@router.get("/notifications/channels", response_model=List[NotificationChannelResponse])
async def list_notification_channels(
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Lista canales de notificación del tenant"""
    tenant_id = current_user["tenant_id"]

    channels = (
        db.query(NotificationChannel)
        .filter(NotificationChannel.tenant_id == tenant_id)
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
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Crea un canal de notificación"""
    tenant_id = current_user["tenant_id"]

    new_channel = NotificationChannel(
        tenant_id=tenant_id,
        tipo=channel_data.tipo,
        name=channel_data.name,
        config=channel_data.config,
        is_active=channel_data.is_active,
        priority=channel_data.priority,
    )

    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)

    return new_channel


@router.put(
    "/notifications/channels/{channel_id}", response_model=NotificationChannelResponse
)
async def update_notification_channel(
    channel_id: UUID,
    channel_update: NotificationChannelUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Actualiza un canal de notificación"""
    tenant_id = current_user["tenant_id"]

    channel = (
        db.query(NotificationChannel)
        .filter(
            and_(
                NotificationChannel.id == channel_id,
                NotificationChannel.tenant_id == tenant_id,
            )
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    update_data = channel_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.commit()
    db.refresh(channel)

    return channel


@router.get("/notifications/log", response_model=List[NotificationLogResponse])
async def get_notification_log(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Obtiene historial de notificaciones"""
    tenant_id = current_user["tenant_id"]

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.tenant_id == tenant_id)
        .order_by(desc(NotificationLog.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return logs
