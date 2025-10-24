"""
Spec1 Routers - Digitalización ventas/compras
"""
from .daily_inventory import router as daily_inventory_router
from .purchase import router as purchase_router
from .milk_record import router as milk_record_router

__all__ = [
    "daily_inventory_router",
    "purchase_router",
    "milk_record_router",
]
