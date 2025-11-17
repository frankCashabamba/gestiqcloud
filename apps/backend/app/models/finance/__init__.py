"""Finance module models"""

from .banco import BankMovement
from .caja import CashClosing, CashMovement

# Keep old names for backward compatibility during migration
BancoMovimiento = BankMovement
CajaMovimiento = CashMovement
CierreCaja = CashClosing

__all__ = [
    "CajaMovimiento",
    "CierreCaja",
    "BankMovement",
    "BancoMovimiento",
    "CashMovement",
    "CashClosing",
]
