"""
Workers Celery para tareas IA programadas.

Tareas:
- daily_executive_summary: Resumen ejecutivo diario para cada tenant activo.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy import text

from app.db.session import get_db_context
from app.modules.notifications.infrastructure._transport import send_smtp
from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger(__name__)


def _build_summary_context(db, tenant_id: str) -> dict[str, Any]:
    """Construye el contexto de negocio del día para el resumen ejecutivo."""
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    # Ventas del día (POS)
    pos = db.execute(
        text(
            "SELECT count(*) AS recibos, coalesce(sum(gross_total), 0) AS total_ventas "
            "FROM pos_receipts WHERE tenant_id = :tid "
            "AND status = 'paid' AND created_at::date = :dia"
        ),
        {"tid": tenant_id, "dia": yesterday},
    ).fetchone()

    # Ventas de órdenes (ventas tradicionales)
    sales = db.execute(
        text(
            "SELECT count(*) AS pedidos, coalesce(sum(total), 0) AS total "
            "FROM sales_orders WHERE tenant_id = :tid AND created_at::date = :dia"
        ),
        {"tid": tenant_id, "dia": yesterday},
    ).fetchone()

    # Productos con stock bajo
    low_stock = db.execute(
        text(
            "SELECT count(*) AS productos_bajo_stock "
            "FROM products p "
            "JOIN stock_items si ON si.product_id = p.id "
            "WHERE p.tenant_id = :tid "
            "AND si.qty <= p.min_stock AND p.min_stock IS NOT NULL AND p.min_stock > 0"
        ),
        {"tid": tenant_id},
    ).fetchone()

    # Compras pendientes de recepción
    pending_purchases = db.execute(
        text(
            "SELECT count(*) AS compras_pendientes "
            "FROM purchases WHERE tenant_id = :tid "
            "AND status IN ('sent', 'confirmed')"
        ),
        {"tid": tenant_id},
    ).fetchone()

    # Día con anomalía de ventas (< 60% promedio)
    anomaly = db.execute(
        text(
            "WITH avg_30 AS ("
            "  SELECT avg(daily_total) AS avg_30d FROM ("
            "    SELECT created_at::date AS dia, sum(gross_total) AS daily_total "
            "    FROM pos_receipts WHERE tenant_id = :tid AND status = 'paid' "
            "    AND created_at > CURRENT_DATE - INTERVAL '30 days' GROUP BY 1"
            "  ) sub"
            ") "
            "SELECT a.avg_30d, "
            "  coalesce(sum(r.gross_total), 0) AS ayer_total "
            "FROM avg_30 a "
            "LEFT JOIN pos_receipts r ON r.tenant_id = :tid "
            "  AND r.status = 'paid' AND r.created_at::date = :dia "
            "GROUP BY a.avg_30d"
        ),
        {"tid": tenant_id, "dia": yesterday},
    ).fetchone()

    return {
        "fecha": str(yesterday),
        "pos_recibos": int(pos[0] or 0) if pos else 0,
        "pos_total_ventas": float(pos[1] or 0) if pos else 0,
        "pedidos_venta": int(sales[0] or 0) if sales else 0,
        "total_pedidos": float(sales[1] or 0) if sales else 0,
        "productos_bajo_stock": int(low_stock[0] or 0) if low_stock else 0,
        "compras_pendientes": int(pending_purchases[0] or 0) if pending_purchases else 0,
        "venta_ayer": float(anomaly[1] or 0) if anomaly else 0,
        "promedio_30d": float(anomaly[0] or 0) if anomaly else 0,
        "anomalia_ventas": (
            anomaly is not None
            and anomaly[0]
            and anomaly[0] > 0
            and (anomaly[1] or 0) < anomaly[0] * 0.6
        ),
    }


def _get_admin_emails(db, tenant_id: str) -> list[str]:
    """Obtiene emails de los administradores activos del tenant."""
    rows = db.execute(
        text(
            "SELECT DISTINCT u.email FROM company_users u "
            "JOIN company_user_roles r ON r.user_id = u.id "
            "WHERE u.tenant_id = :tid AND u.is_active = true "
            "AND r.role IN ('admin', 'owner', 'manager') "
            "AND u.email IS NOT NULL "
            "LIMIT 5"
        ),
        {"tid": tenant_id},
    ).fetchall()
    return [r[0] for r in rows if r[0]]


def _generate_summary_sync(context: dict[str, Any], tenant_name: str) -> str:
    """Llama a AIService de forma síncrona desde Celery."""

    prompt = f"""Eres el asistente de gestión empresarial de GestiqCloud.
Genera un resumen ejecutivo CONCISO del día {context['fecha']} para la empresa: {tenant_name}.

Datos del día:
- Ventas POS: {context['pos_recibos']} recibos · ${context['pos_total_ventas']:.2f}
- Pedidos de venta: {context['pedidos_venta']} · ${context['total_pedidos']:.2f}
- Productos con stock bajo: {context['productos_bajo_stock']}
- Compras pendientes de recepción: {context['compras_pendientes']}
- Promedio ventas POS (30d): ${context['promedio_30d']:.2f}
- Anomalía de ventas detectada: {'SÍ (ventas < 60% del promedio)' if context['anomalia_ventas'] else 'No'}

Genera un resumen ejecutivo en 3-5 puntos clave en español, destacando:
1. Rendimiento de ventas del día
2. Alertas importantes (stock bajo, compras pendientes, anomalías)
3. Recomendación de acción prioritaria

Sé directo y útil. Máximo 200 palabras."""

    async def _run():
        return await AIService.query(
            task=AITask.ANALYSIS,
            prompt=prompt,
            temperature=0.4,
            max_tokens=400,
        )

    response = asyncio.run(_run())

    if response.is_error:
        return _fallback_summary(context, tenant_name)

    return response.content


def _fallback_summary(context: dict[str, Any], tenant_name: str) -> str:
    """Resumen sin IA en caso de error."""
    lines = [
        f"Resumen del {context['fecha']} — {tenant_name}",
        "",
        f"• Ventas POS: {context['pos_recibos']} recibos · ${context['pos_total_ventas']:.2f}",
        f"• Pedidos: {context['pedidos_venta']} · ${context['total_pedidos']:.2f}",
    ]
    if context["productos_bajo_stock"] > 0:
        lines.append(f"⚠️  {context['productos_bajo_stock']} productos con stock bajo")
    if context["compras_pendientes"] > 0:
        lines.append(f"⚠️  {context['compras_pendientes']} compras pendientes de recepción")
    if context["anomalia_ventas"]:
        lines.append("🔴 Anomalía: ventas del día muy por debajo del promedio (< 60%)")
    return "\n".join(lines)


@shared_task(
    bind=True,
    max_retries=2,
    name="app.workers.ai_tasks.daily_executive_summary",
    queue="ai",
)
def daily_executive_summary(self):
    """
    Genera y envía resumen ejecutivo diario por email a los admins de cada tenant activo.
    Se ejecuta a las 07:00 UTC (Celery Beat schedule en celery_config.py).
    """
    logger.info("Iniciando tarea: daily_executive_summary")
    sent_count = 0
    error_count = 0

    with get_db_context() as db:
        # Obtener tenants activos con email configurado
        tenants = db.execute(
            text(
                "SELECT id, name FROM tenants WHERE is_active = true "
                "ORDER BY created_at LIMIT 500"
            )
        ).fetchall()

        for tenant_row in tenants:
            tenant_id = str(tenant_row[0])
            tenant_name = tenant_row[1] or "Empresa"

            try:
                admin_emails = _get_admin_emails(db, tenant_id)
                if not admin_emails:
                    continue

                context = _build_summary_context(db, tenant_id)
                summary_text = _generate_summary_sync(context, tenant_name)

                subject = f"Resumen ejecutivo {context['fecha']} — {tenant_name}"
                body = f"""<html><body>
<h2 style="color:#1e40af">Resumen Ejecutivo Diario</h2>
<p style="color:#6b7280">{context['fecha']} · {tenant_name}</p>
<hr/>
<pre style="font-family:sans-serif;font-size:14px;line-height:1.6">{summary_text}</pre>
<hr/>
<p style="font-size:12px;color:#9ca3af">
  Generado automáticamente por GestiqCloud AI ·
  <a href="#">Ver dashboard completo</a>
</p>
</body></html>"""

                for email in admin_emails:
                    try:
                        send_smtp({}, to=email, subject=subject, body=body)
                        sent_count += 1
                    except Exception as email_err:
                        logger.warning("Error enviando email a %s: %s", email, email_err)

            except Exception as tenant_err:
                logger.error("Error en resumen para tenant %s: %s", tenant_id, tenant_err)
                error_count += 1

    logger.info(
        "daily_executive_summary completado: %d emails enviados, %d errores",
        sent_count,
        error_count,
    )
    return {"sent": sent_count, "errors": error_count}
