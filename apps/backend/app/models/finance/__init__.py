"""Finance module models"""

from .banco import BankMovement
from .caja import CajaMovimiento, CierreCaja

# Keep old name for backward compatibility during migration
BancoMovimiento = BankMovement

__all__ = ["CajaMovimiento", "CierreCaja", "BankMovement", "BancoMovimiento"]
