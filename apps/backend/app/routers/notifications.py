"""
Router API para gestión de notificaciones multi-canal
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.middleware.rls import get_current_tenant_id
from app.models.ai.incident import NotificationChannel, NotificationLog, StockAlert
from app.schemas.notifications import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
    NotificationLogResponse,
    NotificationSendRequest,
    NotificationTestRequest,
    StockAlertResponse,
)

send_notification_task: Any
_celery_import_exception: Exception | None

try:
    from app.workers.notifications import send_notification_task
except ImportError as exc:
    send_notification_task = None
    _celery_import_exception = exc
else:
    _celery_import_exception = None

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_notification_task():
    if send_notification_task is None:
        detail = (
            "Celery no está instalado o no puede importarse; "
            "habilita `celery` y ejecuta los workers para usar notificaciones."
        )
        if _celery_import_exception:
            detail = f"{detail} ({_celery_import_exception})"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
        )
    return send_notification_task


def _resolve_channel_type(payload: Any) -> str | None:
    return getattr(payload, "channel_type", None) or getattr(payload, "tipo", None)


def _channel_to_response(channel: NotificationChannel) -> NotificationChannelResponse:
    return NotificationChannelResponse(
        id=channel.id,
        tenant_id=channel.tenant_id,
        tipo=channel.channel_type,
        name=channel.name,
        description=None,
        config=channel.config,
        active=channel.is_active,
        use_for_alerts=True,
        use_for_invoices=False,
        use_for_marketing=False,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


# ============================================================================
# CHANNELS - Configuración de canales
# ============================================================================


@router.get("/channels", response_model=list[NotificationChannelResponse])
def list_channels(
    channel_type: str | None = Query(
        None, description="Filtrar por tipo: email, whatsapp, telegram"
    ),
    activo: bool | None = Query(None),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Lista todos los canales de notificación configurados"""
    query = db.query(NotificationChannel).filter(NotificationChannel.tenant_id == tenant_id)

    if channel_type:
        query = query.filter(NotificationChannel.channel_type == channel_type)
    if activo is not None:
        query = query.filter(NotificationChannel.is_active == activo)

    channels = query.order_by(NotificationChannel.created_at.desc()).all()
    return [_channel_to_response(c) for c in channels]


@router.post(
    "/channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    payload: NotificationChannelCreate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Crea nuevo canal de notificación

    Tipos soportados:
    - **email**: SMTP (Gmail, SendGrid, etc)
    - **whatsapp**: Twilio o API genérica
    - **telegram**: Bot API
    """
    channel_type = _resolve_channel_type(payload)
    # Validar tipo
    if channel_type not in ["email", "whatsapp", "telegram"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo debe ser: email, whatsapp o telegram",
        )

    # Validar config según tipo
    _validate_channel_config(channel_type, payload.config)

    # Crear canal
    channel = NotificationChannel(
        tenant_id=tenant_id,
        channel_type=channel_type,
        name=payload.name,
        config=payload.config,
        is_active=payload.active,
    )

    db.add(channel)
    db.commit()
    db.refresh(channel)

    return _channel_to_response(channel)


@router.get("/channels/{channel_id}", response_model=NotificationChannelResponse)
def get_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Obtiene detalles de un canal"""
    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    return _channel_to_response(channel)


@router.put("/channels/{channel_id}", response_model=NotificationChannelResponse)
def update_channel(
    channel_id: uuid.UUID,
    payload: NotificationChannelUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Actualiza configuración de canal"""
    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    # Actualizar campos
    update_data = payload.dict(exclude_unset=True)

    # Validar config si se está actualizando
    if "config" in update_data:
        _validate_channel_config(channel.channel_type, update_data["config"])

    if "active" in update_data:
        channel.is_active = update_data.pop("active")
    update_data.pop("description", None)
    update_data.pop("use_for_alerts", None)
    update_data.pop("use_for_invoices", None)
    update_data.pop("use_for_marketing", None)
    for field, value in update_data.items():
        setattr(channel, field, value)

    channel.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(channel)

    return _channel_to_response(channel)


@router.delete("/channels/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Elimina un canal de notificación"""
    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.id == channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    db.delete(channel)
    db.commit()

    return None


@router.post("/test", status_code=status.HTTP_202_ACCEPTED)
def test_notification(
    payload: NotificationTestRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Envía notificación de prueba

    Útil para validar configuración de canales
    """
    # Validar canal existe
    channel = (
        db.query(NotificationChannel)
        .filter(
            NotificationChannel.id == payload.channel_id,
            NotificationChannel.tenant_id == tenant_id,
        )
        .first()
    )

    if not channel:
        raise HTTPException(status_code=404, detail="Canal no encontrado")

    # Mensaje de prueba
    asunto = f"Test desde GestiQCloud - {channel.name}"
    mensaje = f"""
<h2>🧪 Prueba de Notificación</h2>

<p>Este es un mensaje de prueba desde <b>GestiQCloud</b>.</p>

<p><b>Canal:</b> {channel.name} ({channel.channel_type})</p>
<p><b>Fecha:</b> {datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")} UTC</p>

<p>Si recibes este mensaje, tu canal está configurado correctamente ✅</p>
    """.strip()

    # Enviar async
    task = _get_notification_task().delay(
        tenant_id=str(tenant_id),
        channel_type=channel.channel_type,
        destinatario=payload.destinatario,
        asunto=asunto,
        mensaje=mensaje,
        ref_type="test",
        ref_id=str(channel.id),
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Notificación de prueba enviada a {payload.destinatario}",
    }


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
def send_notification(
    payload: NotificationSendRequest,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Envía notificación manual

    Permite enviar notificaciones ad-hoc sin canal pre-configurado
    """
    # Validar config si no usa channel_id
    if not payload.channel_id and not payload.config_override:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe proporcionar channel_id o config_override",
        )

    config = None
    channel_type = _resolve_channel_type(payload)
    if payload.config_override:
        _validate_channel_config(channel_type, payload.config_override)
        config = payload.config_override

    # Enviar async
    task = _get_notification_task().delay(
        tenant_id=str(tenant_id),
        channel_type=channel_type,
        destinatario=payload.destinatario,
        asunto=payload.asunto,
        mensaje=payload.mensaje,
        ref_type=payload.ref_type,
        ref_id=str(payload.ref_id) if payload.ref_id else None,
        config_override=config,
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "message": f"Notificación enviada a {payload.destinatario}",
    }


# ============================================================================
# LOGS - Historial de notificaciones
# ============================================================================


@router.get("/log", response_model=list[NotificationLogResponse])
def list_logs(
    channel_type: str | None = Query(None),
    status_: str | None = Query(None),
    ref_type: str | None = Query(None),
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Lista historial de notificaciones enviadas

    Filtros disponibles:
    - **tipo**: email, whatsapp, telegram
    - **estado**: sent, failed, pending
    - **ref_type**: invoice, stock_alert, payment
    - **days**: Días hacia atrás (default: 7)
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = db.query(NotificationLog).filter(
        NotificationLog.tenant_id == tenant_id,
        NotificationLog.created_at >= cutoff_date,
    )

    if channel_type:
        query = query.filter(NotificationLog.notification_type == channel_type)
    if status_:
        query = query.filter(NotificationLog.status == status_)
    if ref_type:
        query = query.filter(NotificationLog.ref_type == ref_type)

    _total = query.count()

    logs = query.order_by(desc(NotificationLog.created_at)).offset(offset).limit(limit).all()

    return logs


@router.get("/log/stats")
def get_log_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Estadísticas de notificaciones"""
    from sqlalchemy import func

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    # Total por estado
    by_status = (
        db.query(NotificationLog.status, func.count(NotificationLog.id).label("count"))
        .filter(
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.created_at >= cutoff_date,
        )
        .group_by(NotificationLog.status)
        .all()
    )

    # Total por tipo
    by_tipo = (
        db.query(NotificationLog.notification_type, func.count(NotificationLog.id).label("count"))
        .filter(
            NotificationLog.tenant_id == tenant_id,
            NotificationLog.created_at >= cutoff_date,
        )
        .group_by(NotificationLog.notification_type)
        .all()
    )

    return {
        "period_days": days,
        "by_status": {row.status: row.count for row in by_status},
        "by_tipo": {row.channel_type: row.count for row in by_tipo},
        "total": sum(row.count for row in by_status),
    }


# ============================================================================
# ALERTS - Alertas de stock
# ============================================================================


@router.get("/alerts", response_model=list[StockAlertResponse])
def list_stock_alerts(
    status_: str | None = Query("active"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Lista alertas de stock bajo (solo esquema moderno)."""
    base_sql = (
        "SELECT "
        " id, tenant_id, product_id, warehouse_id, "
        " current_qty AS nivel_actual, "
        " threshold_qty AS nivel_minimo, "
        " (threshold_qty - current_qty)::int AS diferencia, "
        " status AS estado, "
        " notified_at, resolved_at, created_at "
        "FROM stock_alerts "
        "WHERE tenant_id = :tid "
    )
    params = {"tid": tenant_id, "lim": int(limit)}
    if status_:
        base_sql += " AND status = :st"
        params["st"] = status_
    base_sql += " ORDER BY (threshold_qty - current_qty) ASC, created_at DESC  LIMIT :lim"

    rows = db.execute(text(base_sql), params).mappings().all()
    # Retornar dicts compatibles con StockAlertResponse
    return [
        {
            "id": r["id"],
            "tenant_id": r["tenant_id"],
            "product_id": r["product_id"],
            "warehouse_id": r["warehouse_id"],
            "nivel_actual": r["nivel_actual"],
            "nivel_minimo": r["nivel_minimo"],
            "diferencia": r["diferencia"],
            "estado": r["estado"],
            "notified_at": r.get("notified_at"),
            "notified_via": None,
            "resolved_at": r.get("resolved_at"),
            "resolved_by": None,
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.post("/alerts/{alert_id}/resolve", status_code=status.HTTP_204_NO_CONTENT)
def resolve_stock_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Marca alerta como resuelta"""
    alert = (
        db.query(StockAlert)
        .filter(StockAlert.id == alert_id, StockAlert.tenant_id == tenant_id)
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")

    alert.status = "resolved"
    alert.resolved_at = datetime.utcnow()
    # TODO: alert.resolved_by = current_user_id

    db.commit()

    return None


# ============================================================================
# HELPERS
# ============================================================================


def _validate_channel_config(tipo: str, config: dict):
    """Valida configuración según tipo de canal"""
    if tipo == "email":
        required = ["smtp_host", "smtp_user", "smtp_password"]
        missing = [f for f in required if not config.get(f)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Config email incompleto. Faltan: {', '.join(missing)}",
            )

    elif tipo == "whatsapp":
        provider = config.get("provider")
        if provider == "twilio":
            required = ["account_sid", "auth_token", "from_number"]
        elif provider == "generic":
            required = ["api_url", "api_key"]
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WhatsApp provider debe ser 'twilio' o 'generic'",
            )

        missing = [f for f in required if not config.get(f)]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Config WhatsApp incompleto. Faltan: {', '.join(missing)}",
            )

    elif tipo == "telegram":
        if not config.get("bot_token"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Config telegram requiere 'bot_token'",
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Tipo no soportado: {tipo}"
        )
