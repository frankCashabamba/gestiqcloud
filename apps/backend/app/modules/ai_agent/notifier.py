from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.ai.incident import Incident, NotificationChannel, NotificationLog, StockAlert


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
        subject = f"[INCIDENCIA {incident.severity.upper()}] {incident.title}"
        body = _build_incident_message(incident)
        recipient = _get_default_recipient(channel)

    # Enviar según tipo de canal
    try:
        if channel.channel_type == "email":
            result = await _send_email(channel, recipient, subject, body)
        elif channel.channel_type == "whatsapp":
            result = await _send_whatsapp(channel, recipient, body)
        elif channel.channel_type == "telegram":
            result = await _send_telegram(channel, recipient, body)
        elif channel.channel_type == "slack":
            result = await _send_slack(channel, subject, body)
        else:
            raise ValueError(f"Tipo de canal no soportado: {channel.channel_type}")

        # Registrar en log
        log_entry = NotificationLog(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            incident_id=incident.id if incident else None,
            stock_alert_id=alert.id if alert else None,
            notification_type=channel.channel_type,
            recipient=recipient,
            subject=subject,
            body=body,
            status="sent",
            sent_at=datetime.now(UTC),
            extra_data=result,
        )
        db.add(log_entry)
        db.commit()

        return {
            "status": "sent",
            "message_id": result.get("message_id"),
            "sent_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        # Registrar error en log
        log_entry = NotificationLog(
            tenant_id=channel.tenant_id,
            channel_id=channel.id,
            incident_id=incident.id if incident else None,
            stock_alert_id=alert.id if alert else None,
            notification_type=channel.channel_type,
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
            "message_id": f"email_{datetime.now(UTC).timestamp()}",
            "status": "sent",
        }

    except ImportError:
        return {
            "message_id": "mock_email_id",
            "status": "sent (mock - install aiosmtplib)",
        }


async def _send_whatsapp(channel: NotificationChannel, recipient: str, body: str) -> dict:
    """Envía WhatsApp via Twilio API."""
    config = channel.config
    account_sid = config.get("twilio_account_sid")
    auth_token = config.get("twilio_auth_token")
    from_number = config.get("twilio_whatsapp_number")  # e.g. "whatsapp:+14155238886"

    if not all([account_sid, auth_token, from_number]):
        return {
            "message_id": "mock_whatsapp_id",
            "status": "sent (mock - configure twilio credentials)",
        }

    to_number = recipient if recipient.startswith("whatsapp:") else f"whatsapp:{recipient}"
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    try:
        import httpx

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                data={"From": from_number, "To": to_number, "Body": body},
                auth=(account_sid, auth_token),
            )
            data = response.json()
            if response.status_code >= 400:
                raise Exception(
                    f"Twilio error {response.status_code}: {data.get('message', 'unknown')}"
                )
            return {
                "message_id": data.get("sid", f"wa_{datetime.now(UTC).timestamp()}"),
                "status": "sent",
            }

    except ImportError:
        return {"message_id": "mock_whatsapp_id", "status": "sent (mock - install httpx)"}


async def _send_telegram(channel: NotificationChannel, recipient: str, body: str) -> dict:
    """Envía mensaje a Telegram via Bot API"""
    config = channel.config
    bot_token = config.get("bot_token")
    chat_id = config.get("chat_id")

    if not bot_token or not chat_id:
        return {"message_id": "mock_telegram_id", "status": "sent (mock)"}

    try:
        import httpx

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": body, "parse_mode": "HTML"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return {"message_id": data["result"]["message_id"], "status": "sent"}

    except ImportError:
        return {
            "message_id": "mock_telegram_id",
            "status": "sent (mock - install httpx)",
        }
    except Exception as e:
        raise Exception(f"Error enviando Telegram: {str(e)}")


async def _send_slack(channel: NotificationChannel, subject: str, body: str) -> dict:
    """Envía mensaje a Slack via Webhook o Bot Token API."""
    config = channel.config
    webhook_url = config.get("webhook_url")
    bot_token = config.get("bot_token")
    slack_channel = config.get("channel", "#alerts")

    if not webhook_url and not bot_token:
        return {
            "message_id": "mock_slack_id",
            "status": "sent (mock - configure webhook_url or bot_token)",
        }

    try:
        import httpx

        async with httpx.AsyncClient() as client:
            if bot_token:
                # Use Slack Web API for richer messages
                url = "https://slack.com/api/chat.postMessage"
                payload = {
                    "channel": slack_channel,
                    "text": f"*{subject}*\n\n{body}",
                    "unfurl_links": False,
                }
                headers = {"Authorization": f"Bearer {bot_token}"}
                response = await client.post(url, json=payload, headers=headers)
                data = response.json()
                if not data.get("ok"):
                    raise Exception(f"Slack API error: {data.get('error', 'unknown')}")
                return {
                    "message_id": data.get("ts", f"slack_{datetime.now(UTC).timestamp()}"),
                    "status": "sent",
                }
            else:
                # Use incoming webhook
                response = await client.post(webhook_url, json={"text": f"*{subject}*\n\n{body}"})
                response.raise_for_status()
                return {
                    "message_id": f"slack_{datetime.now(UTC).timestamp()}",
                    "status": "sent",
                }

    except ImportError:
        return {"message_id": "mock_slack_id", "status": "sent (mock - install httpx)"}


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

Severidad: {incident.severity.upper()}
Tipo: {incident.type}
Título: {incident.title}

Descripción:
{incident.description or "N/A"}

{"🔴 CRÍTICO - Revisar inmediatamente" if incident.severity == "critical" else ""}

ID: {incident.id}
Fecha: {incident.created_at.strftime("%Y-%m-%d %H:%M:%S")}
"""


def _get_default_recipient(channel: NotificationChannel) -> str:
    """Obtiene destinatario por defecto del canal"""
    config = channel.config

    if channel.channel_type == "email":
        return config.get("default_recipient", "admin@example.com")
    elif channel.channel_type == "whatsapp":
        return config.get("phone", "+1234567890")
    elif channel.channel_type == "telegram":
        return config.get("chat_id", "mock_chat_id")
    elif channel.channel_type == "slack":
        return config.get("channel", "#alerts")

    return "unknown"
