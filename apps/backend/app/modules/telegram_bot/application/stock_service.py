"""
Consultas de stock para el bot de Telegram.

Utiliza el campo Product.stock (desnormalizado) para obtener
el inventario actual por tenant. No requiere joins complejos.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core.products import Product

logger = logging.getLogger(__name__)


def _parse_tenant_uuid(tenant_id: str | UUID) -> UUID:
    if isinstance(tenant_id, UUID):
        return tenant_id
    return UUID(str(tenant_id))


def get_stock_completo(db: Session, tenant_id: str | UUID) -> list[dict]:
    """
    Devuelve todos los productos activos del tenant con su stock actual.
    Ordenados alfabéticamente por nombre.
    """
    tid = _parse_tenant_uuid(tenant_id)
    rows = db.execute(
        select(Product.name, Product.sku, Product.stock, Product.unit)
        .where(Product.tenant_id == tid)
        .where(Product.active.is_(True))
        .order_by(Product.name)
    ).all()

    return [
        {
            "name": row[0],
            "sku": row[1],
            "qty": float(row[2] or 0),
            "unit": row[3] or "unit",
        }
        for row in rows
    ]


def get_stock_bajo(
    db: Session,
    tenant_id: str | UUID,
    threshold: float = 5.0,
) -> list[dict]:
    """
    Devuelve productos activos cuyo stock es <= threshold.
    Ordenados de menor a mayor stock.
    """
    tid = _parse_tenant_uuid(tenant_id)
    rows = db.execute(
        select(Product.name, Product.sku, Product.stock, Product.unit)
        .where(Product.tenant_id == tid)
        .where(Product.active.is_(True))
        .where(Product.stock <= threshold)
        .order_by(Product.stock)
    ).all()

    return [
        {
            "name": row[0],
            "sku": row[1],
            "qty": float(row[2] or 0),
            "unit": row[3] or "unit",
        }
        for row in rows
    ]
