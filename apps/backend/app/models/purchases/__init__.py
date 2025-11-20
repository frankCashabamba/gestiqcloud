"""Purchases module models"""

from .compra import Purchase, PurchaseLine

# Keep old names for backward compatibility during migration
Compra = Purchase
CompraLinea = PurchaseLine

__all__ = ["Purchase", "PurchaseLine", "Compra", "CompraLinea"]
