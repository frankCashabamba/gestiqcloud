"""
Employee Department Service - Business logic layer
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.employee_department import EmployeeDepartment


class EmployeeDepartmentService:
    """Service layer for Employee Department operations."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def list(
        self,
        filters: Dict[str, Any] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        List employee departments with filtering and pagination.

        Args:
            filters: Dictionary of filter criteria
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Dictionary with items, total, page, per_page, pages
        """
        filters = filters or {}

        # Build query
        query = self.db.query(EmployeeDepartment).filter(
            EmployeeDepartment.tenant_id == self.tenant_id
        )

        # Apply search filter
        if "search" in filters:
            search_term = f"%{filters['search']}%"
            query = query.filter(
                or_(
                    EmployeeDepartment.name.ilike(search_term),
                    EmployeeDepartment.code.ilike(search_term),
                    EmployeeDepartment.description.ilike(search_term)
                )
            )

        # Apply specific filters
        if "name_contains" in filters:
            query = query.filter(
                EmployeeDepartment.name.ilike(f"%{filters['name_contains']}%")
            )

        if "code_contains" in filters:
            query = query.filter(
                EmployeeDepartment.code.ilike(f"%{filters['code_contains']}%")
            )

        if "is_active" in filters:
            query = query.filter(
                EmployeeDepartment.is_active == filters["is_active"]
            )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }

    def get(self, department_id: str) -> Optional[EmployeeDepartment]:
        """
        Get a specific employee department by ID.

        Args:
            department_id: UUID string of the department

        Returns:
            EmployeeDepartment instance or None if not found
        """
        try:
            dept_uuid = UUID(department_id)
        except ValueError:
            return None

        return self.db.query(EmployeeDepartment).filter(
            EmployeeDepartment.tenant_id == self.tenant_id,
            EmployeeDepartment.id == dept_uuid
        ).first()

    def create(self, data: Dict[str, Any]) -> EmployeeDepartment:
        """
        Create a new employee department.

        Args:
            data: Dictionary with department data

        Returns:
            Created EmployeeDepartment instance
        """
        department = EmployeeDepartment(
            tenant_id=self.tenant_id,
            **data
        )

        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)

        return department

    def update(self, department_id: str, data: Dict[str, Any]) -> Optional[EmployeeDepartment]:
        """
        Update an employee department.

        Args:
            department_id: UUID string of the department
            data: Dictionary with updated data

        Returns:
            Updated EmployeeDepartment instance or None if not found
        """
        department = self.get(department_id)
        if not department:
            return None

        # Update fields
        for field, value in data.items():
            if hasattr(department, field):
                setattr(department, field, value)

        self.db.commit()
        self.db.refresh(department)

        return department

    def delete(self, department_id: str) -> bool:
        """
        Delete an employee department.

        Args:
            department_id: UUID string of the department

        Returns:
            True if deleted, False if not found
        """
        department = self.get(department_id)
        if not department:
            return False

        self.db.delete(department)
        self.db.commit()

        return True

    def bulk_create(self, items: List[Dict[str, Any]]) -> List[EmployeeDepartment]:
        """
        Create multiple employee departments at once.

        Args:
            items: List of department data dictionaries

        Returns:
            List of created EmployeeDepartment instances
        """
        departments = []
        for item_data in items:
            department = EmployeeDepartment(
                tenant_id=self.tenant_id,
                **item_data
            )
            departments.append(department)

        self.db.add_all(departments)
        self.db.commit()

        # Refresh all to get IDs
        for department in departments:
            self.db.refresh(department)

        return departments

    def get_active_count(self) -> int:
        """
        Get count of active employee departments.

        Returns:
            Number of active departments
        """
        return self.db.query(EmployeeDepartment).filter(
            EmployeeDepartment.tenant_id == self.tenant_id,
            EmployeeDepartment.is_active == True
        ).count()

    def find_by_code(self, code: str) -> Optional[EmployeeDepartment]:
        """
        Find employee department by code.

        Args:
            code: Department code to search for

        Returns:
            EmployeeDepartment instance or None if not found
        """
        return self.db.query(EmployeeDepartment).filter(
            EmployeeDepartment.tenant_id == self.tenant_id,
            EmployeeDepartment.code == code,
            EmployeeDepartment.is_active == True
        ).first()
