"""
Servicio de alertas de caducidad para productos con fecha de vencimiento.

Sectores: farmacia, alimentos, cosméticos, etc.
Consulta la tabla `product_lots` para detectar lotes próximos a vencer o ya vencidos.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ExpiryAlertService:
    """Servicio para consultar alertas de caducidad de productos por lote."""

    @staticmethod
    def check_expiring_products(
        db: Session,
        tenant_id: str,
        days_ahead: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Retorna productos/lotes que vencen dentro de los próximos N días.

        Args:
            db: Sesión de base de datos.
            tenant_id: UUID del tenant.
            days_ahead: Días hacia adelante para buscar vencimientos.

        Returns:
            Lista de diccionarios con información de lotes próximos a vencer.
        """
        cutoff_date = datetime.now(UTC).date() + timedelta(days=days_ahead)
        today = datetime.now(UTC).date()

        rows = db.execute(
            text(
                "SELECT pl.id, pl.lot_number, pl.expiry_date, pl.qty, "
                "       pl.warehouse_id, p.id AS product_id, p.name AS product_name "
                "FROM product_lots pl "
                "JOIN products p ON p.id = pl.product_id AND p.tenant_id = pl.tenant_id "
                "WHERE pl.tenant_id = :tid "
                "  AND pl.expiry_date >= :today "
                "  AND pl.expiry_date <= :cutoff "
                "  AND pl.qty > 0 "
                "ORDER BY pl.expiry_date ASC"
            ),
            {"tid": tenant_id, "today": today, "cutoff": cutoff_date},
        ).fetchall()

        return [
            {
                "lot_id": str(r[0]),
                "lot_number": r[1],
                "expiry_date": r[2].isoformat() if r[2] else None,
                "qty": float(r[3]) if r[3] else 0,
                "warehouse_id": str(r[4]) if r[4] else None,
                "product_id": str(r[5]),
                "product_name": r[6],
                "days_until_expiry": (r[2] - today).days if r[2] else None,
            }
            for r in rows
        ]

    @staticmethod
    def check_expired_products(
        db: Session,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """
        Retorna productos/lotes que ya están vencidos y aún tienen stock.

        Args:
            db: Sesión de base de datos.
            tenant_id: UUID del tenant.

        Returns:
            Lista de diccionarios con información de lotes vencidos.
        """
        today = datetime.now(UTC).date()

        rows = db.execute(
            text(
                "SELECT pl.id, pl.lot_number, pl.expiry_date, pl.qty, "
                "       pl.warehouse_id, p.id AS product_id, p.name AS product_name "
                "FROM product_lots pl "
                "JOIN products p ON p.id = pl.product_id AND p.tenant_id = pl.tenant_id "
                "WHERE pl.tenant_id = :tid "
                "  AND pl.expiry_date < :today "
                "  AND pl.qty > 0 "
                "ORDER BY pl.expiry_date ASC"
            ),
            {"tid": tenant_id, "today": today},
        ).fetchall()

        return [
            {
                "lot_id": str(r[0]),
                "lot_number": r[1],
                "expiry_date": r[2].isoformat() if r[2] else None,
                "qty": float(r[3]) if r[3] else 0,
                "warehouse_id": str(r[4]) if r[4] else None,
                "product_id": str(r[5]),
                "product_name": r[6],
                "days_expired": (today - r[2]).days if r[2] else None,
            }
            for r in rows
        ]

    @staticmethod
    def get_expiry_summary(
        db: Session,
        tenant_id: str,
    ) -> dict[str, Any]:
        """
        Retorna un resumen de caducidad para el dashboard.

        Incluye conteos de lotes vencidos, próximos a vencer (7, 30, 90 días),
        y el valor total en riesgo.

        Args:
            db: Sesión de base de datos.
            tenant_id: UUID del tenant.

        Returns:
            Diccionario con conteos y resumen de caducidad.
        """
        today = datetime.now(UTC).date()

        row = db.execute(
            text(
                "SELECT "
                "  COUNT(*) FILTER (WHERE pl.expiry_date < :today) AS expired, "
                "  COUNT(*) FILTER (WHERE pl.expiry_date >= :today "
                "    AND pl.expiry_date <= :today + INTERVAL '7 days') AS expiring_7d, "
                "  COUNT(*) FILTER (WHERE pl.expiry_date >= :today "
                "    AND pl.expiry_date <= :today + INTERVAL '30 days') AS expiring_30d, "
                "  COUNT(*) FILTER (WHERE pl.expiry_date >= :today "
                "    AND pl.expiry_date <= :today + INTERVAL '90 days') AS expiring_90d, "
                "  COUNT(*) AS total_lots_with_expiry "
                "FROM product_lots pl "
                "WHERE pl.tenant_id = :tid "
                "  AND pl.qty > 0 "
                "  AND pl.expiry_date IS NOT NULL"
            ),
            {"tid": tenant_id, "today": today},
        ).fetchone()

        return {
            "date": today.isoformat(),
            "expired_lots": int(row[0] or 0) if row else 0,
            "expiring_7d": int(row[1] or 0) if row else 0,
            "expiring_30d": int(row[2] or 0) if row else 0,
            "expiring_90d": int(row[3] or 0) if row else 0,
            "total_lots_with_expiry": int(row[4] or 0) if row else 0,
        }
