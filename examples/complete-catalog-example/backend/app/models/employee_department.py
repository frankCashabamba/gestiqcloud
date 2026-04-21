"""
Employee Department Model - Example using BaseCatalogModel
"""

from app.models.base import BaseCatalogModel


class EmployeeDepartment(BaseCatalogModel):
    """Employee Department model - follows catalog pattern"""

    __tablename__ = "employee_departments"
    __table_args__ = {"extend_existing": True}
