"""
Example endpoints demonstrating the use of new decorators and utilities.
This shows how to reduce code duplication in catalog CRUD operations.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.decorators.validation import (
    handle_not_found,
    tenant_required,
    validate_pagination_params,
    validate_resource_exists,
    validate_uuid,
)
from app.models.company.company import BusinessType
from app.utils.schema_generator import (
    create_catalog_schemas,
    create_filter_schema,
    create_paginated_response_schema,
)

# Generate schemas automatically (no more manual duplication!)
schemas = create_catalog_schemas("BusinessType")
BusinessTypeBase = schemas["Base"]
BusinessTypeCreate = schemas["Create"]
BusinessTypeUpdate = schemas["Update"]
BusinessTypeResponse = schemas["Response"]

# Generate filter and response schemas
BusinessTypeFilters = create_filter_schema(
    "BusinessType",
    searchable_fields=["name", "code"],
    filterable_fields={"is_active": bool}
)
BusinessTypePaginatedResponse = create_paginated_response_schema(BusinessTypeResponse)

router = APIRouter(prefix="/business-types", tags=["business-types"])


def get_business_type(db: Session, tenant_id: str, business_type_id: str) -> BusinessType | None:
    """Helper function to get a business type by ID."""
    return db.query(BusinessType).filter(
        BusinessType.tenant_id == tenant_id,
        BusinessType.id == business_type_id
    ).first()


@router.get("/", response_model=BusinessTypePaginatedResponse)
@tenant_required
@validate_pagination_params
def list_business_types(
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
    List business types with filtering and pagination.
    
    Notice how we don't need manual validation of page/per_page
    and tenant_id is automatically extracted.
    """
    query = db.query(BusinessType).filter(BusinessType.tenant_id == tenant_id)
    
    # Apply filters
    if search:
        query = query.filter(
            BusinessType.name.ilike(f"%{search}%") |
            BusinessType.code.ilike(f"%{search}%")
        )
    
    if name_contains:
        query = query.filter(BusinessType.name.ilike(f"%{name_contains}%"))
    
    if code_contains:
        query = query.filter(BusinessType.code.ilike(f"%{code_contains}%"))
    
    if is_active is not None:
        query = query.filter(BusinessType.is_active == is_active)
    
    # Apply pagination
    total = query.count()
    offset = (page - 1) * per_page
    items = query.offset(offset).limit(per_page).all()
    
    return BusinessTypePaginatedResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/{business_type_id}", response_model=BusinessTypeResponse)
@tenant_required
@validate_resource_exists(get_business_type, "BusinessType")
def get_business_type(
    request: Request,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
    business_type_id: str = None,
    validated_business_type: BusinessType = None,  # Added by validate_resource_exists decorator
) -> BusinessType:
    """
    Get a specific business type by ID.
    
    Notice how we don't need manual UUID validation
    or existence checks - decorators handle it!
    """
    return validated_business_type


@router.post("/", response_model=BusinessTypeResponse, status_code=201)
@tenant_required
def create_business_type(
    request: Request,
    business_type_data: BusinessTypeCreate,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> BusinessType:
    """
    Create a new business type.
    
    The schema is automatically generated, so no manual schema definition needed.
    """
    business_type = BusinessType(
        tenant_id=tenant_id,
        **business_type_data.model_dump(exclude_unset=True)
    )
    db.add(business_type)
    db.commit()
    db.refresh(business_type)
    return business_type


@router.put("/{business_type_id}", response_model=BusinessTypeResponse)
@tenant_required
@handle_not_found("Business Type")
def update_business_type(
    request: Request,
    business_type_id: str,
    business_type_data: BusinessTypeUpdate,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> BusinessType:
    """
    Update a business type.
    
    UUID validation and error handling are automatic.
    """
    # Validate UUID
    business_type_uuid = validate_uuid(business_type_id, "business_type_id")
    
    # Get existing business type
    business_type = get_business_type(db, tenant_id, str(business_type_uuid))
    if not business_type:
        raise HTTPException(status_code=404, detail="Business Type not found")
    
    # Update fields
    update_data = business_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(business_type, field, value)
    
    db.commit()
    db.refresh(business_type)
    return business_type


@router.delete("/{business_type_id}", status_code=204)
@tenant_required
@handle_not_found("Business Type")
def delete_business_type(
    request: Request,
    business_type_id: str,
    db: Session = Depends(get_db),
    tenant_id: str = None,  # Added by tenant_required decorator
) -> None:
    """
    Delete a business type.
    
    All validation is handled by decorators.
    """
    # Validate UUID
    business_type_uuid = validate_uuid(business_type_id, "business_type_id")
    
    # Get and delete business type
    business_type = get_business_type(db, tenant_id, str(business_type_uuid))
    if not business_type:
        raise HTTPException(status_code=404, detail="Business Type not found")
    
    db.delete(business_type)
    db.commit()


# Example of how to create similar endpoints for other catalogs
# Just change the model and regenerate schemas - no code duplication!

# For BusinessCategory:
# from app.models.company.company import BusinessCategory
# def get_business_category(db: Session, tenant_id: str, category_id: str) -> BusinessCategory | None:
#     return db.query(BusinessCategory).filter(
#         BusinessCategory.tenant_id == tenant_id,
#         BusinessCategory.id == category_id
#     ).first()
#
# schemas = create_catalog_schemas("BusinessCategory")
# # ... reuse the same endpoint patterns with just the model changed
