"""Expense Category Model - Catalog Pattern"""

from app.models.base import BaseCatalogModel


class ExpenseCategory(BaseCatalogModel):
    """Expense Category model - follows catalog pattern"""

    __tablename__ = "expense_categories"
    __table_args__ = {"extend_existing": True}
