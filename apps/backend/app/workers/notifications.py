"""
Workers Celery para notificaciones multi-canal.
Las funciones de envío real viven en:
  app.modules.notifications.infrastructure._transport
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task

from app.db.session import get_db_context
from app.models.ai.incident import NotificationChannel, NotificationLog, StockAlert
from app.modules.notifications.infrastructure._transport import (
    send_smtp,
    send_telegram,
    send_whatsapp,
)

# ---------------------------------------------------------------------------
# Tarea principal: enviar una notificación
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3)
def send_notification_task(
    self,
    tenant_id: str,
    channel_type: str,
    destinatario: str,
    asunto: str,
    message: str,
    ref_type: str | None = None,
    ref_id: str | None = None,
    config_override: dict[str, Any] | None = None,
):
    """
    Envía una notificación por el canal configurado y persiste el log.

    Args:
        tenant_id:       UUID del tenant (str)
        channel_type:    'email' | 'whatsapp' | 'telegram'
        destinatario:    email / teléfono / chat_id
        asunto:          Asunto del mensaje
        message:         Cuerpo (HTML para email)
        ref_type:        Tipo de referencia ('invoice', 'stock_alert', …)
        ref_id:          UUID del documento relacionado
        config_override: Config custom (omite la BD de canales)
    """
    with get_db_context() as db:
        # 1. Obtener configuración del canal
        if config_override:
            config = config_override
        else:
            channel_row = (
                db.query(NotificationChannel)
                .filter(
                    NotificationChannel.tenant_id == tenant_id,
                    NotificationChannel.channel_type == channel_type,
                    NotificationChannel.is_active.is_(True),
                )
                .order_by(NotificationChannel.priority.desc())
                .first()
            )
            if not channel_row:
                raise ValueError(
                    f"Canal '{channel_type}' no configurado o inactivo para tenant {tenant_id}"
                )
            config = channel_row.config

        # 2. Enviar
        try:
            if channel_type == "email":
                result = send_smtp(config, destinatario, asunto, message)
            elif channel_type in ("whatsapp", "sms"):
                result = send_whatsapp(config, destinatario, message)
            elif channel_type == "telegram":
                result = send_telegram(config, destinatario, message)
            else:
                raise ValueError(f"Canal no soportado: {channel_type}")

            status = "sent"
            error_msg = None
        except Exception as exc:
            status = "failed"
            error_msg = str(exc)
            result = {}
            # Guardar log de error antes de reintentar
            _write_log(
                db,
                tenant_id,
                channel_type,
                destinatario,
                asunto,
                message,
                status,
                error_msg,
                ref_type,
                ref_id,
            )
            db.commit()
            raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))

        # 3. Log exitoso
        log = _write_log(
            db,
            tenant_id,
            channel_type,
            destinatario,
            asunto,
            message,
            status,
            error_msg,
            ref_type,
            ref_id,
            extra_data=result,
        )
        db.commit()

        return {"status": status, "log_id": str(log.id), "result": result}


# ---------------------------------------------------------------------------
# Tarea programada: alertas de stock bajo
# ---------------------------------------------------------------------------


@shared_task
def check_and_notify_low_stock():
    """
    Revisión periódica de stock bajo y envío de notificaciones.
    Ejecutar cada hora vía Celery Beat.
    """
    from sqlalchemy import text

    with get_db_context() as db:
        db.execute(text("SELECT check_low_stock()"))
        db.commit()

        alerts = (
            db.query(StockAlert)
            .filter(StockAlert.status == "active", StockAlert.notified_at.is_(None))
            .all()
        )

        if not alerts:
            return {"message": "No hay alertas pendientes", "count": 0}

        # Agrupar por tenant
        by_tenant: dict[str, list[StockAlert]] = {}
        for alert in alerts:
            key = str(alert.tenant_id)
            by_tenant.setdefault(key, []).append(alert)

        notified_count = 0
        for tenant_id, tenant_alerts in by_tenant.items():
            channels = (
                db.query(NotificationChannel)
                .filter(
                    NotificationChannel.tenant_id == tenant_id,
                    NotificationChannel.is_active.is_(True),
                )
                .all()
            )
            if not channels:
                continue

            productos_list = [
                f"- <b>{a.product.name}</b>: {a.current_qty} uds (mínimo: {a.threshold_qty})"
                for a in tenant_alerts
            ]
            body = (
                f"<b>⚠️ Alerta de Stock Bajo</b>\n\n"
                f"Tienes {len(tenant_alerts)} producto(s) con stock bajo:\n\n"
                + "\n".join(productos_list)
            )

            channels_used = []
            for ch in channels:
                default_recipient = ch.config.get("default_recipient")
                if not default_recipient:
                    continue
                try:
                    send_notification_task.delay(
                        tenant_id=tenant_id,
                        channel_type=ch.channel_type,
                        destinatario=default_recipient,
                        asunto="⚠️ Alerta Stock Bajo",
                        message=body,
                        ref_type="stock_alert",
                    )
                    channels_used.append(ch.channel_type)
                except Exception as exc:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Error encolando alerta para %s: %s", ch.channel_type, exc
                    )

            if channels_used:
                now = datetime.now(UTC)
                for alert in tenant_alerts:
                    alert.notified_at = now
                    alert.status = "notified"
                db.commit()
                notified_count += 1

        return {"notified_tenants": notified_count, "total_alerts": len(alerts)}


# ---------------------------------------------------------------------------
# Tarea programada: alertas de caducidad (farmacia / alimentos)
# ---------------------------------------------------------------------------


@shared_task(name="app.workers.notifications.check_expiry_alerts")
def check_expiry_alerts(days_ahead: int = 30):
    """
    Detecta lotes con fecha de caducidad próxima y envía alertas.
    Ejecutar diariamente vía Celery Beat.

    Args:
        days_ahead: Aviso con tantos días de antelación (default: 30).
    """
    from sqlalchemy import text

    with get_db_context() as db:
        # Buscar lotes que caducan en los próximos `days_ahead` días y tienen stock > 0
        rows = db.execute(
            text(
                "SELECT si.tenant_id, p.name AS product_name, si.lot, si.expires_at, "
                "si.qty, w.name AS warehouse_name, "
                "(si.expires_at - CURRENT_DATE) AS days_left "
                "FROM stock_items si "
                "JOIN products p ON p.id = si.product_id "
                "JOIN warehouses w ON w.id = si.warehouse_id "
                "WHERE si.expires_at IS NOT NULL "
                "AND si.expires_at BETWEEN CURRENT_DATE AND CURRENT_DATE + :days "
                "AND si.qty > 0 "
                "ORDER BY si.tenant_id, si.expires_at ASC"
            ),
            {"days": days_ahead},
        ).fetchall()

        if not rows:
            return {"message": "Sin lotes próximos a caducar", "count": 0}

        # Agrupar por tenant
        by_tenant: dict[str, list] = {}
        for row in rows:
            key = str(row[0])
            by_tenant.setdefault(key, []).append(row)

        notified_count = 0
        for tenant_id, expiry_rows in by_tenant.items():
            channels = (
                db.query(NotificationChannel)
                .filter(
                    NotificationChannel.tenant_id == tenant_id,
                    NotificationChannel.is_active.is_(True),
                )
                .all()
            )
            if not channels:
                continue

            lines = []
            for r in expiry_rows:
                days_left = int(r[6] or 0)
                icon = "🔴" if days_left <= 7 else ("🟡" if days_left <= 15 else "🟢")
                lines.append(
                    f"{icon} <b>{r[1]}</b> | Lote: {r[2] or 'N/A'} | "
                    f"Caduca: {r[3]} ({days_left}d) | Stock: {float(r[4]):.1f} | {r[5]}"
                )

            body = (
                f"<h3>⏰ Alerta de Caducidad — {len(expiry_rows)} lote(s) próximos a vencer</h3>"
                "<ul>" + "".join(f"<li>{ln}</li>" for ln in lines) + "</ul>"
                f"<p style='color:#6b7280;font-size:12px'>Productos que caducan en los próximos {days_ahead} días con stock disponible.</p>"
            )

            for ch in channels:
                default_recipient = ch.config.get("default_recipient")
                if not default_recipient:
                    continue
                try:
                    send_notification_task.delay(
                        tenant_id=tenant_id,
                        channel_type=ch.channel_type,
                        destinatario=default_recipient,
                        asunto=f"⏰ Alerta caducidad: {len(expiry_rows)} lote(s) próximos a vencer",
                        message=body,
                        ref_type="expiry_alert",
                    )
                    notified_count += 1
                except Exception as exc:
                    import logging as _logging

                    _logging.getLogger(__name__).warning(
                        "Error encolando alerta caducidad para tenant %s: %s", tenant_id, exc
                    )

        return {"notified_tenants": notified_count, "total_lots": len(rows)}


# ---------------------------------------------------------------------------
# Tarea: notificar factura al cliente
# ---------------------------------------------------------------------------


@shared_task
def send_invoice_notification(invoice_id: str, channel_type: str = "email"):
    """Notifica al cliente sobre una factura emitida."""
    with get_db_context() as db:
        from app.models.core import Invoice

        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Factura {invoice_id} no encontrada")

        asunto = f"Factura {invoice.numero} - {invoice.empresa.name}"
        currency_symbols = {
            "EUR": "€",
            "USD": "$",
            "GBP": "£",
            "PEN": "S/",
            "MXN": "$",
            "COP": "$",
            "ARS": "$",
            "CLP": "$",
            "BRL": "R$",
            "JPY": "¥",
        }
        iso = getattr(invoice.empresa, "base_currency", None) or "EUR"
        symbol = currency_symbols.get(iso, iso)
        body = (
            f"<h2>Factura #{invoice.numero}</h2>"
            f"<p><b>Fecha:</b> {invoice.fecha.strftime('%d/%m/%Y')}</p>"
            f"<p><b>Cliente:</b> {invoice.cliente.name if invoice.cliente else 'N/A'}</p>"
            f"<p><b>Total:</b> {invoice.total} {symbol}</p>"
            f"<p><b>Estado:</b> {invoice.status}</p>"
        )

        destinatario = None
        if channel_type == "email" and invoice.cliente:
            destinatario = invoice.cliente.email
        elif channel_type == "whatsapp" and invoice.cliente:
            destinatario = invoice.cliente.phone

        if not destinatario:
            raise ValueError(f"Sin destinatario '{channel_type}' para la factura {invoice_id}")

        send_notification_task.delay(
            tenant_id=str(invoice.tenant_id),
            channel_type=channel_type,
            destinatario=destinatario,
            asunto=asunto,
            message=body,
            ref_type="invoice",
            ref_id=str(invoice.id),
        )

        return {"status": "queued", "invoice_id": invoice_id}


# ---------------------------------------------------------------------------
# Tarea: limpieza de logs antiguos
# ---------------------------------------------------------------------------


@shared_task
def cleanup_old_logs(days: int = 90):
    """Elimina logs de notificaciones enviadas con más de `days` días."""
    with get_db_context() as db:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        deleted = (
            db.query(NotificationLog)
            .filter(
                NotificationLog.created_at < cutoff,
                NotificationLog.status == "sent",
            )
            .delete()
        )
        db.commit()
        return {"deleted_logs": deleted, "days": days}


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------


def _write_log(
    db,
    tenant_id: str,
    channel_type: str,
    recipient: str,
    subject: str,
    body: str,
    status: str,
    error_message: str | None = None,
    ref_type: str | None = None,
    ref_id: str | None = None,
    extra_data: dict | None = None,
) -> NotificationLog:
    log = NotificationLog(
        tenant_id=tenant_id,
        notification_type=channel_type,
        recipient=recipient,
        subject=subject,
        body=body,
        status=status,
        error_message=error_message,
        extra_data=extra_data,
        sent_at=datetime.now(UTC) if status == "sent" else None,
    )
    db.add(log)
    return log
