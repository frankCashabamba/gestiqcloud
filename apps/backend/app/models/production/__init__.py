"""Production models."""

from __future__ import annotations

import os

from app.models.production import _production_order


def _is_enabled() -> bool:
    """Return True when the production module should be exposed."""

    raw = os.getenv("ENABLE_PRODUCTION_MODULE", "true")
    return raw.lower() not in {"false", "0", "no", "off"}


if _is_enabled():
    ProductionOrder = _production_order.ProductionOrder
    ProductionOrderLine = _production_order.ProductionOrderLine
    __all__ = ["ProductionOrder", "ProductionOrderLine"]
else:
    __all__ = []
