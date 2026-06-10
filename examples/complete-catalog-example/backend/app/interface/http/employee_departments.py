"""
Employee Department Endpoints - Example using validation decorators
"""

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.decorators.validation import (
    handle_not_found,
    tenant_required,
    validate_pagination_params,
    validate_resource_exists,
    validate_uuid,
)
from app.models.employee_department import EmployeeDepartment
from app.schemas.employee_department import (
    EmployeeDepartmentCreate,
    EmployeeDepartmentResponse,
    EmployeeDepartmentUpdate,
)
from app.services.employee_department import EmployeeDepartmentService
from app.utils.schema_generator import (
    create_filter_schema,
    create_paginated_response_schema,
)

# Create filter and response schemas automatically
EmployeeDepartmentFilters = create_filter_schema(
    "EmployeeDepartment",
    searchable_fields=["name", "code"],
    filterable_fields={"is_active": bool}
)
EmployeeDepartmentPaginatedResponse = create_paginated_response_schema(EmployeeDepartmentResponse)

router = APIRouter(prefix="/employee-departments", tags=["employee-departments"])


def get_employee_department(db: Session, tenant_id: str, dept_id: str) -> EmployeeDepartment | None:
    """Helper function to get an employee department by ID."""
    return db.query(EmployeeDepartment).filter(
        EmployeeDepartment.tenant_id == tenant_id,
        EmployeeDepartment.id == dept_id
    ).first()


@router.get("/", response_model=EmployeeDepartmentPaginatedResponse)
@tenant_required
@validate_pagination_params
def list_employee_departments(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
    page: int = 1,
    per_page: int = 20,
    search: str = None,
    is_active: bool = None,
    name_contains: str = None,
    code_contains: str = None,
) -> Any:
    """
    List employee departments with filtering and pagination.

    Notice how validation is automatic - no manual checks needed!
    """
    service = EmployeeDepartmentService(db, tenant_id)

    # Build filters
    filters = {}
    if search:
        filters["search"] = search
    if is_active is not None:
        filters["is_active"] = is_active
    if name_contains:
        filters["name_contains"] = name_contains
    if code_contains:
        filters["code_contains"] = code_contains

    # Get paginated results
    result = service.list(filters, page, per_page)

    return EmployeeDepartmentPaginatedResponse(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        per_page=result["per_page"],
        pages=result["pages"]
    )


@router.get("/{department_id}", response_model=EmployeeDepartmentResponse)
@tenant_required
@validate_resource_exists(get_employee_department, "Employee Department")
def get_employee_department(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
    department_id: str = None,
    validated_employee_department: EmployeeDepartment = None,  # Added by validate_resource_exists decorator
) -> EmployeeDepartment:
    """
    Get a specific employee department by ID.

    All validation is handled by decorators!
    """
    return validated_employee_department


@router.post("/", response_model=EmployeeDepartmentResponse, status_code=201)
@tenant_required
def create_employee_department(
    request: Request,
    department_data: EmployeeDepartmentCreate,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> EmployeeDepartment:
    """
    Create a new employee department.

    Schema is auto-generated, validation is automatic.
    """
    service = EmployeeDepartmentService(db, tenant_id)
    return service.create(department_data.model_dump(exclude_unset=True))


@router.put("/{department_id}", response_model=EmployeeDepartmentResponse)
@tenant_required
@handle_not_found("Employee Department")
def update_employee_department(
    request: Request,
    department_id: str,
    department_data: EmployeeDepartmentUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> EmployeeDepartment:
    """
    Update an employee department.

    UUID validation and error handling are automatic.
    """
    # Validate UUID (automatic error handling)
    dept_uuid = validate_uuid(department_id, "department_id")

    service = EmployeeDepartmentService(db, tenant_id)
    return service.update(str(dept_uuid), department_data.model_dump(exclude_unset=True))


@router.delete("/{department_id}", status_code=204)
@tenant_required
@handle_not_found("Employee Department")
def delete_employee_department(
    request: Request,
    department_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> None:
    """
    Delete an employee department.

    All validation is handled by decorators!
    """
    # Validate UUID (automatic error handling)
    dept_uuid = validate_uuid(department_id, "department_id")

    service = EmployeeDepartmentService(db, tenant_id)
    service.delete(str(dept_uuid))


# This replaces ~100 lines of manual validation and error handling:
#
# @router.get("/{department_id}")
# def get_employee_department(department_id: str, request: Request):
#     try:
#         dept_uuid = UUID(department_id)
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid department_id")
#
#     claims = getattr(request.state, "access_claims", {})
#     tenant_id = claims.get("tenant_id")
#     if not tenant_id:
#         raise HTTPException(status_code=400, detail="Tenant not found")
#
#     department = db.query(EmployeeDepartment).filter(
#         EmployeeDepartment.tenant_id == tenant_id,
#         EmployeeDepartment.id == str(dept_uuid)
#     ).first()
#
#     if not department:
#         raise HTTPException(status_code=404, detail="Employee Department not found")
#
#     return department
