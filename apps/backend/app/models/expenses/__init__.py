"""Expenses module models"""

from .gasto import Expense

# Keep old name for backward compatibility during migration
Gasto = Expense

__all__ = ["Expense", "Gasto"]
