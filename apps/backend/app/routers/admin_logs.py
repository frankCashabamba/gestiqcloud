"""Admin logs router — NotificationLog y AuditEvent en /api/v1/admin/logs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.tenant import get_current_user
from app.models.ai.incident import NotificationChannel, NotificationLog
from app.models.core.audit_event import AuditEvent
from app.models.tenant import Tenant

router = APIRouter(prefix="/logs", tags=["Admin Logs"])


class LogEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    tipo: str
    canal: str | None = None
    destinatario: str
    asunto: str | None = None
    mensaje: str | None = None
    estado: str
    extra_data: dict[str, Any] | None = None
    error_message: str | None = None
    ref_type: str | None = None
    ref_id: str | None = None
    sent_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LogStatsResponse(BaseModel):
    period_days: int
    total: int
    by_status: dict[str, int]
    by_tipo: dict[str, int]


def _to_response(log: NotificationLog, channel_map: dict) -> LogEntryResponse:
    canal = None
    if log.channel_id and log.channel_id in channel_map:
        canal = channel_map[log.channel_id]

    ref_type = None
    ref_id = None
    if log.incident_id:
        ref_type = "incident"
        ref_id = str(log.incident_id)
    elif log.stock_alert_id:
        ref_type = "stock_alert"
        ref_id = str(log.stock_alert_id)
    elif log.extra_data and isinstance(log.extra_data, dict):
        ref_type = log.extra_data.get("ref_type")
        ref_id = log.extra_data.get("ref_id")

    return LogEntryResponse(
        id=log.id,
        tenant_id=log.tenant_id,
        tipo=log.notification_type,
        canal=canal,
        destinatario=log.recipient,
        asunto=log.subject,
        mensaje=log.body,
        estado=log.status,
        extra_data=log.extra_data,
        error_message=log.error_message,
        ref_type=ref_type,
        ref_id=ref_id,
        sent_at=log.sent_at,
        created_at=log.created_at,
    )


@router.get("/", response_model=list[LogEntryResponse])
async def list_logs(
    tipo: str | None = None,
    estado: str | None = None,
    ref_type: str | None = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Lista de notification logs del tenant con filtros."""
    tenant_id = current_user["tenant_id"]
    since = datetime.now(UTC) - timedelta(days=days)

    query = db.query(NotificationLog).filter(
        and_(
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.created_at >= since,
        )
    )

    if tipo:
        query = query.filter(NotificationLog.notification_type == tipo)
    if estado:
        query = query.filter(NotificationLog.status == estado)
    if ref_type == "incident":
        query = query.filter(NotificationLog.incident_id.isnot(None))
    elif ref_type == "stock_alert":
        query = query.filter(NotificationLog.stock_alert_id.isnot(None))

    logs = query.order_by(desc(NotificationLog.created_at)).offset(offset).limit(limit).all()

    # Cargar canales en bulk para evitar N+1
    channel_ids = {log.channel_id for log in logs if log.channel_id}
    channel_map: dict = {}
    if channel_ids:
        channels = (
            db.query(NotificationChannel).filter(NotificationChannel.id.in_(channel_ids)).all()
        )
        channel_map = {c.id: c.channel_type for c in channels}

    return [_to_response(log, channel_map) for log in logs]


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Estadísticas de logs del tenant para los últimos N días."""
    tenant_id = current_user["tenant_id"]
    since = datetime.now(UTC) - timedelta(days=days)

    base_filter = and_(
        NotificationLog.tenant_id == tenant_id,
        NotificationLog.created_at >= since,
    )

    total = db.query(func.count(NotificationLog.id)).filter(base_filter).scalar() or 0

    by_status_rows = (
        db.query(NotificationLog.status, func.count(NotificationLog.id))
        .filter(base_filter)
        .group_by(NotificationLog.status)
        .all()
    )

    by_tipo_rows = (
        db.query(NotificationLog.notification_type, func.count(NotificationLog.id))
        .filter(base_filter)
        .group_by(NotificationLog.notification_type)
        .all()
    )

    return LogStatsResponse(
        period_days=days,
        total=total,
        by_status={row[0]: row[1] for row in by_status_rows},
        by_tipo={row[0]: row[1] for row in by_tipo_rows},
    )


# ============================================================================
# AUDIT EVENTS — acciones de usuarios (create/update/delete) en todos los módulos
# ============================================================================


class AuditEntryResponse(BaseModel):
    id: UUID
    tenant_id: UUID | None = None
    tenant_name: str | None = None
    user_id: UUID | None = None
    actor_type: str
    action: str
    entity_type: str
    entity_id: str | None = None
    source: str
    changes: dict[str, Any] | None = None
    ip: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditStatsResponse(BaseModel):
    period_days: int
    total: int
    by_action: dict[str, int]
    by_entity_type: dict[str, int]
    by_tenant: list[dict[str, Any]]


@router.get("/audit", response_model=list[AuditEntryResponse])
def list_audit_events(
    tenant_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    search: str | None = None,
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """
    Lista de audit events de TODOS los tenants (superadmin).
    Filtrable por tenant_id, acción, entidad o búsqueda libre.
    """
    since = datetime.now(UTC) - timedelta(days=days)

    query = db.query(AuditEvent).filter(AuditEvent.created_at >= since)

    if tenant_id:
        query = query.filter(AuditEvent.tenant_id == tenant_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if entity_type:
        query = query.filter(AuditEvent.entity_type == entity_type)
    if search:
        query = query.filter(
            or_(
                AuditEvent.entity_id.ilike(f"%{search}%"),
                AuditEvent.entity_type.ilike(f"%{search}%"),
            )
        )

    events = query.order_by(desc(AuditEvent.created_at)).offset(offset).limit(limit).all()

    # Bulk-load tenant names
    tenant_ids = {e.tenant_id for e in events if e.tenant_id}
    tenant_name_map: dict = {}
    if tenant_ids:
        tenants = db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(tenant_ids)).all()
        tenant_name_map = {t.id: t.name for t in tenants}

    result = []
    for ev in events:
        entry = AuditEntryResponse(
            id=ev.id,
            tenant_id=ev.tenant_id,
            tenant_name=tenant_name_map.get(ev.tenant_id) if ev.tenant_id else None,
            user_id=ev.user_id,
            actor_type=ev.actor_type,
            action=ev.action,
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            source=ev.source,
            changes=ev.changes,
            ip=ev.ip,
            created_at=ev.created_at,
        )
        result.append(entry)
    return result


@router.get("/audit/stats", response_model=AuditStatsResponse)
def get_audit_stats(
    tenant_id: str | None = None,
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    """Estadísticas de audit events: totales por acción, entidad y top tenants."""
    since = datetime.now(UTC) - timedelta(days=days)
    base = [AuditEvent.created_at >= since]
    if tenant_id:
        base.append(AuditEvent.tenant_id == tenant_id)

    total = db.query(func.count(AuditEvent.id)).filter(and_(*base)).scalar() or 0

    by_action = {
        row[0]: row[1]
        for row in db.query(AuditEvent.action, func.count(AuditEvent.id))
        .filter(and_(*base))
        .group_by(AuditEvent.action)
        .all()
    }

    by_entity = {
        row[0]: row[1]
        for row in db.query(AuditEvent.entity_type, func.count(AuditEvent.id))
        .filter(and_(*base))
        .group_by(AuditEvent.entity_type)
        .order_by(desc(func.count(AuditEvent.id)))
        .limit(20)
        .all()
    }

    top_tenants_rows = (
        db.query(AuditEvent.tenant_id, func.count(AuditEvent.id).label("total"))
        .filter(and_(*base))
        .group_by(AuditEvent.tenant_id)
        .order_by(desc("total"))
        .limit(10)
        .all()
    )
    tenant_ids = {r[0] for r in top_tenants_rows if r[0]}
    tenant_name_map: dict = {}
    if tenant_ids:
        tenants = db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(tenant_ids)).all()
        tenant_name_map = {t.id: t.name for t in tenants}

    by_tenant = [
        {
            "tenant_id": str(r[0]) if r[0] else None,
            "tenant_name": tenant_name_map.get(r[0]) if r[0] else "sistema",
            "total": r[1],
        }
        for r in top_tenants_rows
    ]

    return AuditStatsResponse(
        period_days=days,
        total=total,
        by_action=by_action,
        by_entity_type=by_entity,
        by_tenant=by_tenant,
    )
