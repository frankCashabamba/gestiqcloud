"""Expense Category Model - Entity Pattern"""

from app.models.base import BaseTransactionalModel


class ExpenseCategory(BaseTransactionalModel):
    """Expense Category model - follows catalog pattern"""

    __tablename__ = "expense_categories"
    __table_args__ = {"extend_existing": True}
