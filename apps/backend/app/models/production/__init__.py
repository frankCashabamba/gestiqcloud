"""Production models."""

from __future__ import annotations

from app.models.production import _production_order

ProductionOrder = _production_order.ProductionOrder
ProductionOrderLine = _production_order.ProductionOrderLine

__all__ = ["ProductionOrder", "ProductionOrderLine"]
