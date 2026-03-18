"""
Workers Celery para alertas de caducidad de productos.

Tareas:
- check_expiry_alerts: Revisión diaria de productos próximos a vencer por tenant.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from sqlalchemy import text

from app.db.session import get_db_context
from app.modules.inventory.application.expiry_alerts import ExpiryAlertService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    name="app.workers.expiry_tasks.check_expiry_alerts",
    queue="notifications",
)
def check_expiry_alerts(self, days_ahead: int = 30) -> dict[str, Any]:
    """
    Revisa productos próximos a vencer para cada tenant activo.
    Se ejecuta a las 06:00 UTC (Celery Beat schedule en celery_config.py).

    Args:
        days_ahead: Días hacia adelante para buscar vencimientos.

    Returns:
        Diccionario con totales procesados.
    """
    logger.info("Iniciando tarea: check_expiry_alerts (days_ahead=%d)", days_ahead)
    tenants_checked = 0
    total_expiring = 0
    total_expired = 0

    with get_db_context() as db:
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
                expiring = ExpiryAlertService.check_expiring_products(
                    db, tenant_id, days_ahead=days_ahead
                )
                expired = ExpiryAlertService.check_expired_products(db, tenant_id)

                if expiring:
                    logger.warning(
                        "Tenant %s (%s): %d lotes próximos a vencer en %d días",
                        tenant_id,
                        tenant_name,
                        len(expiring),
                        days_ahead,
                    )
                    total_expiring += len(expiring)

                if expired:
                    logger.warning(
                        "Tenant %s (%s): %d lotes ya vencidos con stock",
                        tenant_id,
                        tenant_name,
                        len(expired),
                    )
                    total_expired += len(expired)

                tenants_checked += 1

            except Exception as err:
                logger.error(
                    "Error revisando caducidad para tenant %s: %s",
                    tenant_id,
                    err,
                )

    logger.info(
        "check_expiry_alerts completado: %d tenants, %d lotes por vencer, %d vencidos",
        tenants_checked,
        total_expiring,
        total_expired,
    )
    return {
        "tenants_checked": tenants_checked,
        "total_expiring": total_expiring,
        "total_expired": total_expired,
    }
