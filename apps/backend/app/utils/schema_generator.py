"""
Utility for generating common Pydantic schemas to reduce duplication.
"""

from typing import Any, Dict, Optional, Type, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import DeclarativeBase


def create_catalog_schemas(
    model_name: str,
    base_model: Optional[Type[BaseModel]] = None,
    include_tenant: bool = True,
    extra_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Type[BaseModel]]:
    """
    Generate standard CRUD schemas for catalog-like entities.
    
    Args:
        model_name: Name of the model (e.g., "BusinessType")
        base_model: Optional base model with common fields
        include_tenant: Whether to include tenant_id in schemas
        extra_fields: Additional fields to include in Base schema
        
    Returns:
        Dictionary with Base, Create, Update, and Response schemas
    """
    
    # Define base fields
    base_fields = {
        "name": (str, Field(..., min_length=1, max_length=100)),
        "code": (Optional[str], Field(None, max_length=50)),
        "description": (Optional[str], Field(None)),
        "is_active": (bool, Field(default=True)),
    }
    
    if include_tenant:
        base_fields["tenant_id"] = (Optional[UUID], Field(None))
    
    # Add extra fields if provided
    if extra_fields:
        base_fields.update(extra_fields)
    
    # Create Base schema
    class_dict = {"__annotations__": base_fields.copy()}
    
    # Add model config
    class_dict["model_config"] = ConfigDict(
        from_attributes=True,
        extra="forbid" if not extra_fields else "allow"
    )
    
    # Create Base class
    BaseSchema = type(f"{model_name}Base", (BaseModel,), class_dict)
    
    # Create Create schema (inherits from Base, no additional fields)
    CreateSchema = type(f"{model_name}Create", (BaseSchema,), {})
    
    # Create Update schema (all fields optional)
    update_fields = {}
    for field_name, field_type in base_fields.items():
        if field_name == "tenant_id":
            continue  # Don't allow updating tenant_id
        # Make fields optional for update
        if isinstance(field_type, tuple):
            field_type = (Optional[field_type[0]], field_type[1])
        else:
            field_type = (Optional[field_type], Field(...))
        update_fields[field_name] = field_type
    
    update_class_dict = {"__annotations__": update_fields}
    update_class_dict["model_config"] = ConfigDict(from_attributes=True)
    
    UpdateSchema = type(f"{model_name}Update", (BaseModel,), update_class_dict)
    
    # Create Response schema (includes id and timestamps)
    response_fields = base_fields.copy()
    response_fields.update({
        "id": (UUID, Field(...)),
        "created_at": (str, Field(...)),  # Using str for datetime serialization
        "updated_at": (str, Field(...)),
    })
    
    if include_tenant:
        response_fields["tenant_id"] = (UUID, Field(...))
    
    response_class_dict = {"__annotations__": response_fields}
    response_class_dict["model_config"] = ConfigDict(from_attributes=True)
    
    ResponseSchema = type(f"{model_name}Response", (BaseModel,), response_class_dict)
    
    return {
        "Base": BaseSchema,
        "Create": CreateSchema,
        "Update": UpdateSchema,
        "Response": ResponseSchema,
    }


def create_paginated_response_schema(item_schema: Type[BaseModel]) -> Type[BaseModel]:
    """
    Create a paginated response schema for any item type.
    
    Args:
        item_schema: Schema for the items in the response
        
    Returns:
        Paginated response schema
    """
    
    class PaginatedResponse(BaseModel):
        items: list[item_schema]
        total: int
        page: int
        per_page: int
        pages: int
        
        model_config = ConfigDict(from_attributes=True)
    
    return PaginatedResponse


def create_filter_schema(
    model_name: str,
    searchable_fields: Optional[list[str]] = None,
    filterable_fields: Optional[Dict[str, Type]] = None
) -> Type[BaseModel]:
    """
    Create a filter schema for list endpoints.
    
    Args:
        model_name: Name of the model
        searchable_fields: List of fields that can be searched
        filterable_fields: Dict of field names to types for filtering
        
    Returns:
        Filter schema
    """
    
    filter_fields = {
        "page": (Optional[int], Field(default=1, ge=1)),
        "per_page": (Optional[int], Field(default=20, ge=1, le=1000)),
        "search": (Optional[str], Field(None)),
    }
    
    # Add searchable fields
    if searchable_fields:
        for field in searchable_fields:
            filter_fields[f"{field}_contains"] = (Optional[str], Field(None))
    
    # Add filterable fields
    if filterable_fields:
        filter_fields.update(filterable_fields)
    
    class_dict = {"__annotations__": filter_fields}
    class_dict["model_config"] = ConfigDict(extra="forbid")
    
    FilterSchema = type(f"{model_name}Filters", (BaseModel,), class_dict)
    
    return FilterSchema


# Predefined common schema sets
CATALOG_SCHEMAS = {
    "BusinessType": create_catalog_schemas("BusinessType"),
    "BusinessCategory": create_catalog_schemas("BusinessCategory"),
    "SectorTemplate": create_catalog_schemas(
        "SectorTemplate",
        extra_fields={
            "template_config": (Optional[Dict[str, Any]], Field(default_factory=dict)),
            "config_version": (Optional[int], Field(None)),
        }
    ),
    "Language": create_catalog_schemas("Language", include_tenant=False),
    "Currency": create_catalog_schemas(
        "Currency", 
        include_tenant=False,
        extra_fields={"symbol": (str, Field(..., max_length=5))}
    ),
    "Country": create_catalog_schemas("Country", include_tenant=False),
    "Weekday": create_catalog_schemas(
        "Weekday",
        include_tenant=False,
        extra_fields={
            "key": (str, Field(..., max_length=20)),
            "order": (int, Field(...)),
        }
    ),
}


def get_catalog_schemas(model_name: str) -> Dict[str, Type[BaseModel]]:
    """
    Get predefined schemas for a catalog model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dictionary with Base, Create, Update, Response schemas
    """
    return CATALOG_SCHEMAS.get(model_name, create_catalog_schemas(model_name))


# Example usage:
# from app.utils.schema_generator import get_catalog_schemas
# 
# schemas = get_catalog_schemas("BusinessType")
# BusinessTypeBase = schemas["Base"]
# BusinessTypeCreate = schemas["Create"]
# BusinessTypeUpdate = schemas["Update"]
# BusinessTypeResponse = schemas["Response"]
