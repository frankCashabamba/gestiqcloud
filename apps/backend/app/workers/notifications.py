"""
Workers Celery para notificaciones multi-canal
Soporta: Email (SMTP), WhatsApp (Twilio/API), Telegram (Bot API)
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import requests
from celery import shared_task
from sqlalchemy import text

from app.db.session import get_db_context
from app.models.ai.incident import NotificationChannel, NotificationLog, StockAlert


@shared_task(bind=True, max_retries=3)
def send_notification_task(
    self,
    tenant_id: str,
    tipo: str,
    destinatario: str,
    asunto: str,
    mensaje: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
    config_override: dict[str, Any] | None = None,
):
    """
    Envía notificación por canal configurado

    Args:
        tenant_id: UUID del tenant
        tipo: 'email', 'whatsapp', 'telegram'
        destinatario: email/phone/chat_id
        asunto: Asunto del mensaje
        mensaje: Cuerpo del mensaje (HTML para email)
        ref_type: Tipo de referencia ('invoice', 'stock_alert', etc)
        ref_id: UUID del documento relacionado
        config_override: Configuración custom (opcional)
    """
    with get_db_context() as db:
        try:
            # 1. Obtener canal configurado
            if not config_override:
                channel = (
                    db.query(NotificationChannel)
                    .filter(
                        NotificationChannel.tenant_id == tenant_id,
                        NotificationChannel.tipo == tipo,
                        NotificationChannel.active,
                    )
                    .first()
                )

                if not channel:
                    raise ValueError(f"Canal {tipo} no configurado o inactivo")

                config = channel.config
            else:
                config = config_override

            # 2. Enviar según tipo
            result = None
            if tipo == "email":
                result = send_email(config, destinatario, asunto, mensaje)
            elif tipo == "whatsapp":
                result = send_whatsapp(config, destinatario, mensaje)
            elif tipo == "telegram":
                result = send_telegram(config, destinatario, mensaje)
            else:
                raise ValueError(f"Tipo de notificación no soportado: {tipo}")

            # 3. Log exitoso
            log = NotificationLog(
                tenant_id=tenant_id,
                tipo=tipo,
                destinatario=destinatario,
                asunto=asunto,
                mensaje=mensaje,
                canal=tipo,
                estado="sent",
                ref_type=ref_type,
                ref_id=ref_id,
                metadata=result,
                sent_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()

            return {"status": "sent", "log_id": str(log.id), "result": result}

        except Exception as e:
            # Log error
            log = NotificationLog(
                tenant_id=tenant_id,
                tipo=tipo,
                destinatario=destinatario,
                asunto=asunto,
                mensaje=mensaje,
                canal=tipo,
                estado="failed",
                error_message=str(e),
                ref_type=ref_type,
                ref_id=ref_id,
            )
            db.add(log)
            db.commit()

            # Retry con backoff exponencial
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))


def send_email(config: dict[str, Any], to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Envía email vía SMTP

    Config esperado:
    - smtp_host: Servidor SMTP
    - smtp_port: Puerto (587/465)
    - smtp_user: Usuario
    - smtp_password: Contraseña
    - from_email: Remitente
    - use_tls: True/False
    """
    smtp_host = config.get("smtp_host", os.getenv("SMTP_HOST", "smtp.gmail.com"))
    smtp_port = config.get("smtp_port", int(os.getenv("SMTP_PORT", "587")))
    smtp_user = config.get("smtp_user", os.getenv("SMTP_USER"))
    smtp_pass = config.get("smtp_password", os.getenv("SMTP_PASSWORD"))
    from_email = config.get("from_email", smtp_user)
    use_tls = config.get("use_tls", True)

    if not smtp_user or not smtp_pass:
        raise ValueError("SMTP credentials no configurados")

    # Crear mensaje
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    # Añadir versión HTML
    html_part = MIMEText(body, "html", "utf-8")
    msg.attach(html_part)

    # Enviar
    if use_tls:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    return {"sent": True, "to": to, "from": from_email, "subject": subject}


def send_whatsapp(config: dict[str, Any], phone: str, message: str) -> dict[str, Any]:
    """
    Envía WhatsApp vía Twilio o API genérica

    Config para Twilio:
    - provider: 'twilio'
    - account_sid: Twilio Account SID
    - auth_token: Twilio Auth Token
    - from_number: Número WhatsApp (+14155238886)

    Config para API genérica:
    - provider: 'generic'
    - api_url: URL del endpoint
    - api_key: Bearer token
    """
    provider = config.get("provider", "twilio")

    if provider == "twilio":
        try:
            from twilio.rest import Client
        except ImportError:
            raise ImportError("Instalar twilio: pip install twilio")

        account_sid = config.get("account_sid")
        auth_token = config.get("auth_token")
        from_number = config.get("from_number")

        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Configuración Twilio incompleta")

        client = Client(account_sid, auth_token)
        msg = client.messages.create(
            from_=f"whatsapp:{from_number}", body=message, to=f"whatsapp:{phone}"
        )

        return {
            "sent": True,
            "provider": "twilio",
            "message_sid": msg.sid,
            "status": msg.status,
        }

    elif provider == "generic":
        api_url = config.get("api_url")
        api_key = config.get("api_key")

        if not api_url or not api_key:
            raise ValueError("API URL y API Key requeridos")

        response = requests.post(
            api_url,
            json={"phone": phone, "message": message},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        response.raise_for_status()

        return {"sent": True, "provider": "generic", "response": response.json()}

    else:
        raise ValueError(f"Provider WhatsApp no soportado: {provider}")


def send_telegram(config: dict[str, Any], chat_id: str, message: str) -> dict[str, Any]:
    """
    Envía mensaje vía Telegram Bot API

    Config:
    - bot_token: Token del bot (obtener de @BotFather)
    - parse_mode: 'HTML' o 'Markdown' (default: HTML)
    """
    bot_token = config.get("bot_token")
    parse_mode = config.get("parse_mode", "HTML")

    if not bot_token:
        raise ValueError("bot_token no configurado")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    response = requests.post(
        url,
        json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    return {
        "sent": True,
        "message_id": data["result"]["message_id"],
        "chat_id": chat_id,
    }


@shared_task
def check_and_notify_low_stock():
    """
    Tarea programada: revisar stock bajo y notificar
    Ejecuta cada hora vía Celery Beat
    """
    with get_db_context() as db:
        # 1. Ejecutar función SQL que genera alertas
        db.execute(text("SELECT check_low_stock()"))
        db.commit()

        # 2. Obtener alertas activas no notificadas
        alerts = (
            db.query(StockAlert)
            .filter(StockAlert.estado == "active", StockAlert.notified_at is None)
            .all()
        )

        if not alerts:
            return {"message": "No hay alertas pendientes", "count": 0}

        # 3. Agrupar por tenant
        by_tenant: dict[str, list[StockAlert]] = {}
        for alert in alerts:
            tenant_id = str(alert.tenant_id)
            if tenant_id not in by_tenant:
                by_tenant[tenant_id] = []
            by_tenant[tenant_id].append(alert)

        # 4. Enviar notificación por tenant
        notified_count = 0
        for tenant_id, tenant_alerts in by_tenant.items():
            # Obtener canales activos
            channels = (
                db.query(NotificationChannel)
                .filter(
                    NotificationChannel.tenant_id == tenant_id,
                    NotificationChannel.active,
                )
                .all()
            )

            if not channels:
                continue

            # Construir mensaje
            productos_list = []
            for alert in tenant_alerts:
                productos_list.append(
                    f"- <b>{alert.product.name}</b>: {alert.nivel_actual} uds "
                    f"(mínimo: {alert.nivel_minimo})"
                )

            mensaje = f"""
<b>⚠️ Alerta de Stock Bajo</b>

Tienes {len(tenant_alerts)} producto(s) con stock bajo:

{chr(10).join(productos_list)}

<a href="https://app.gestiqcloud.com/inventario">Ver Inventario Completo</a>
            """.strip()

            # Enviar por cada canal
            channels_used = []
            for channel in channels:
                default_recipient = channel.config.get("default_recipient")
                if not default_recipient:
                    continue

                try:
                    send_notification_task.delay(
                        tenant_id=tenant_id,
                        tipo=channel.tipo,
                        destinatario=default_recipient,
                        asunto="⚠️ Alerta Stock Bajo",
                        mensaje=mensaje,
                        ref_type="stock_alert",
                        ref_id=None,
                    )
                    channels_used.append(channel.tipo)
                except Exception as e:
                    print(f"Error enviando alerta por {channel.tipo}: {e}")

            # Marcar como notificadas
            if channels_used:
                for alert in tenant_alerts:
                    alert.notified_at = datetime.utcnow()
                    alert.notified_via = channels_used
                    alert.estado = "notified"
                db.commit()
                notified_count += 1

        return {"notified_tenants": notified_count, "total_alerts": len(alerts)}


@shared_task
def send_invoice_notification(invoice_id: str, tipo: str = "email"):
    """
    Notifica al cliente sobre una factura

    Args:
        invoice_id: UUID de la factura
        tipo: 'email', 'whatsapp', 'telegram'
    """
    with get_db_context() as db:
        from app.models.core import Invoice

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Factura {invoice_id} no encontrada")

        # Construir mensaje
        asunto = f"Factura {invoice.numero} - {invoice.empresa.name}"
        mensaje = f"""
<h2>Factura #{invoice.numero}</h2>

<p><b>Fecha:</b> {invoice.fecha.strftime("%d/%m/%Y")}</p>
<p><b>Cliente:</b> {invoice.cliente.name if invoice.cliente else "N/A"}</p>
<p><b>Total:</b> {invoice.total} €</p>

<p><b>Estado:</b> {invoice.estado}</p>

<a href="https://app.gestiqcloud.com/invoices/{invoice.id}">Ver Factura Completa</a>
        """.strip()

        # Destinatario
        destinatario = None
        if tipo == "email" and invoice.cliente:
            destinatario = invoice.cliente.email
        elif tipo == "whatsapp" and invoice.cliente:
            destinatario = invoice.cliente.phone

        if not destinatario:
            raise ValueError(f"No hay destinatario {tipo} configurado")

        # Enviar
        send_notification_task.delay(
            tenant_id=str(invoice.tenant_id),
            tipo=tipo,
            destinatario=destinatario,
            asunto=asunto,
            mensaje=mensaje,
            ref_type="invoice",
            ref_id=str(invoice.id),
        )

        return {"status": "queued", "invoice_id": invoice_id}


@shared_task
def cleanup_old_logs(days: int = 90):
    """
    Limpia logs de notificaciones antiguos
    Ejecutar mensualmente vía Celery Beat
    """
    with get_db_context() as db:
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        deleted = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.created_at < cutoff_date,
                NotificationLog.estado == "sent",
            )
            .delete()
        )

        db.commit()

        return {"deleted_logs": deleted, "days": days}
