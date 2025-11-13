from datetime import datetime
from typing import Any

from app.models.ai.incident import Incident, NotificationChannel, NotificationLog, StockAlert
from sqlalchemy.orm import Session


async def send_notification(
    channel: NotificationChannel,
    alert: StockAlert = None,
    incident: Incident = None,
    db: Session = None,
) -> dict[str, Any]:
    """
    Envía notificación a través del canal configurado

    Args:
        channel: Canal de notificación (email, whatsapp, telegram, slack)
        alert: Alerta de stock (opcional)
        incident: Incidencia (opcional)
        db: Sesión de base de datos

    Returns:
        Dict con status, message_id, sent_at
    """
    if not alert and not incident:
        raise ValueError("Debe proporcionar alert o incident")

    # Construir mensaje
    if alert:
        subject = f"[ALERTA STOCK] {alert.alert_type.upper()}"
        body = _build_stock_alert_message(alert)
        recipient = _get_default_recipient(channel)
    elif incident:
        subject = f"[INCIDENCIA {incident.severidad.upper()}] {incident.titulo}"
        body = _build_incident_message(incident)
        recipient = _get_default_recipient(channel)

    # Enviar según tipo de canal
    try:
        if channel.tipo == "email":
            result = await _send_email(channel, recipient, subject, body)
        elif channel.tipo == "whatsapp":
            result = await _send_whatsapp(channel, recipient, body)
        elif channel.tipo == "telegram":
            result = await _send_telegram(channel, recipient, body)
        elif channel.tipo == "slack":
            result = await _send_slack(channel, subject, body)
        else:
            raise ValueError(f"Tipo de canal no soportado: {channel.tipo}")

        # Registrar en log
        log_entry = NotificationLog(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            incident_id=incident.id if incident else None,
            stock_alert_id=alert.id if alert else None,
            tipo=channel.tipo,
            recipient=recipient,
            subject=subject,
            body=body,
            status="sent",
            sent_at=datetime.utcnow(),
            metadata=result,
        )
        db.add(log_entry)
        db.commit()

        return {
            "status": "sent",
            "message_id": result.get("message_id"),
            "sent_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        # Registrar error en log
        log_entry = NotificationLog(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            incident_id=incident.id if incident else None,
            stock_alert_id=alert.id if alert else None,
            tipo=channel.tipo,
            recipient=recipient,
            subject=subject,
            body=body,
            status="failed",
            error_message=str(e),
        )
        db.add(log_entry)
        db.commit()

        raise Exception(f"Error enviando notificación: {str(e)}")


# ============================================================================
# ENVÍO POR CANAL
# ============================================================================


async def _send_email(
    channel: NotificationChannel, recipient: str, subject: str, body: str
) -> dict:
    """Envía email via SMTP"""
    config = channel.config
    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    from_email = config.get("from_email")

    # Mock en desarrollo
    if not all([smtp_host, smtp_user, smtp_password, from_email]):
        return {"message_id": "mock_email_id", "status": "sent (mock)"}

    # Implementación real con aiosmtplib
    try:
        from email.message import EmailMessage

        import aiosmtplib

        message = EmailMessage()
        message["From"] = from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )

        return {
            "message_id": f"email_{datetime.utcnow().timestamp()}",
            "status": "sent",
        }

    except ImportError:
        return {
            "message_id": "mock_email_id",
            "status": "sent (mock - install aiosmtplib)",
        }


async def _send_whatsapp(channel: NotificationChannel, recipient: str, body: str) -> dict:
    """Envía WhatsApp via API (ej. Twilio, WhatsApp Business API)"""
    config = channel.config
    api_key = config.get("api_key")
    _phone = config.get("_phone")

    # Mock en desarrollo
    if not api_key:
        return {"message_id": "mock_whatsapp_id", "status": "sent (mock)"}

    # Implementación real con API provider (ej. Twilio)
    # TODO: Implementar con aiohttp
    return {
        "message_id": f"wa_{datetime.utcnow().timestamp()}",
        "status": "sent (stub)",
    }


async def _send_telegram(channel: NotificationChannel, recipient: str, body: str) -> dict:
    """Envía mensaje a Telegram via Bot API"""
    config = channel.config
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")

    if not bot_token or not chat_id:
        return {"message_id": "mock_telegram_id", "status": "sent (mock)"}

    try:
        import aiohttp

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": body, "parse_mode": "HTML"}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return {"message_id": data["result"]["message_id"], "status": "sent"}

    except ImportError:
        return {
            "message_id": "mock_telegram_id",
            "status": "sent (mock - install aiohttp)",
        }
    except Exception as e:
        raise Exception(f"Error enviando Telegram: {str(e)}")


async def _send_slack(channel: NotificationChannel, subject: str, body: str) -> dict:
    """Envía mensaje a Slack via Webhook"""
    config = channel.config
    webhook_url = config.get("webhook_url")

    if not webhook_url:
        return {"message_id": "mock_slack_id", "status": "sent (mock)"}

    try:
        import aiohttp

        payload = {"text": f"*{subject}*\n\n{body}"}

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                response.raise_for_status()
                return {
                    "message_id": f"slack_{datetime.utcnow().timestamp()}",
                    "status": "sent",
                }

    except ImportError:
        return {
            "message_id": "mock_slack_id",
            "status": "sent (mock - install aiohttp)",
        }
    except Exception as e:
        raise Exception(f"Error enviando Slack: {str(e)}")


# ============================================================================
# HELPERS
# ============================================================================


def _build_stock_alert_message(alert: StockAlert) -> str:
    """Construye mensaje de alerta de stock"""
    return f"""
🚨 ALERTA DE STOCK

Tipo: {alert.alert_type.upper()}
Producto: {alert.product_id}
Cantidad actual: {alert.current_qty}
Umbral: {alert.threshold_qty}

{"⚠️ REQUIERE ACCIÓN INMEDIATA" if alert.alert_type == "out_of_stock" else ""}

Revisa el sistema para más detalles.
"""


def _build_incident_message(incident: Incident) -> str:
    """Construye mensaje de incidencia"""
    return f"""
⚠️ INCIDENCIA DETECTADA

Severidad: {incident.severidad.upper()}
Tipo: {incident.tipo}
Título: {incident.titulo}

Descripción:
{incident.description or "N/A"}

{"🔴 CRÍTICO - Revisar inmediatamente" if incident.severidad == "critical" else ""}

ID: {incident.id}
Fecha: {incident.created_at.strftime("%Y-%m-%d %H:%M:%S")}
"""


def _get_default_recipient(channel: NotificationChannel) -> str:
    """Obtiene destinatario por defecto del canal"""
    config = channel.config

    if channel.tipo == "email":
        return config.get("default_recipient", "admin@example.com")
    elif channel.tipo == "whatsapp":
        return config.get("phone", "+1234567890")
    elif channel.tipo == "telegram":
        return config.get("chat_id", "mock_chat_id")
    elif channel.tipo == "slack":
        return config.get("channel", "#alerts")

    return "unknown"
