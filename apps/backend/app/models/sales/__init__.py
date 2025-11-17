"""Sales module models"""

from .venta import Sale

# Keep old name for backward compatibility during migration
Venta = Sale

__all__ = ["Sale", "Venta"]
