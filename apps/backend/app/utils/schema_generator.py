"""
Utility for generating common Pydantic schemas to reduce duplication.
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, create_model


def create_catalog_schemas(
    model_name: str,
    base_model: type[BaseModel] | None = None,
    include_tenant: bool = True,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, type[BaseModel]]:
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
        "code": (str | None, Field(default=None, max_length=50)),
        "description": (str | None, Field(default=None)),
        "is_active": (bool, Field(default=True)),
    }

    if include_tenant:
        base_fields["tenant_id"] = (UUID | None, Field(default=None))

    # Add extra fields if provided
    if extra_fields:
        base_fields.update(extra_fields)

    # Create Base schema
    BaseSchema = create_model(
        f"{model_name}Base",
        __config__=ConfigDict(
            from_attributes=True, extra="forbid" if not extra_fields else "allow"
        ),
        **base_fields,
    )

    # Create Create schema (inherits from Base, no additional fields)
    CreateSchema = create_model(f"{model_name}Create", __base__=BaseSchema)

    # Create Update schema (all fields optional)
    update_fields = {}

    def _optional_annotation(annotation: Any) -> Any:
        if isinstance(annotation, str):
            return annotation if "None" in annotation else f"{annotation} | None"
        try:
            return annotation | None
        except TypeError:
            return annotation

    for field_name, field_type in base_fields.items():
        if field_name == "tenant_id":
            continue  # Don't allow updating tenant_id
        # Make fields optional for update without turning them into required fields again.
        if isinstance(field_type, tuple):
            update_fields[field_name] = (_optional_annotation(field_type[0]), None)
        else:
            update_fields[field_name] = (_optional_annotation(field_type), None)

    UpdateSchema = create_model(
        f"{model_name}Update",
        __config__=ConfigDict(from_attributes=True),
        **update_fields,
    )

    # Create Response schema (includes id and timestamps)
    response_fields = base_fields.copy()
    response_fields.update(
        {
            "id": (UUID, Field(...)),
            "created_at": (str, Field(...)),  # Using str for datetime serialization
            "updated_at": (str, Field(...)),
        }
    )

    if include_tenant:
        response_fields["tenant_id"] = (UUID, Field(...))

    ResponseSchema = create_model(
        f"{model_name}Response",
        __config__=ConfigDict(from_attributes=True),
        **response_fields,
    )

    return {
        "Base": BaseSchema,
        "Create": CreateSchema,
        "Update": UpdateSchema,
        "Response": ResponseSchema,
    }


def create_paginated_response_schema(item_schema: type[BaseModel]) -> type[BaseModel]:
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
    searchable_fields: list[str] | None = None,
    filterable_fields: dict[str, type] | None = None,
) -> type[BaseModel]:
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
        "page": (int | None, Field(default=1, ge=1)),
        "per_page": (int | None, Field(default=20, ge=1, le=1000)),
        "search": (str | None, Field(None)),
    }

    # Add searchable fields
    if searchable_fields:
        for field in searchable_fields:
            filter_fields[f"{field}_contains"] = (str | None, Field(None))

    # Add filterable fields
    if filterable_fields:
        filter_fields.update(filterable_fields)

    FilterSchema = create_model(
        f"{model_name}Filters",
        __config__=ConfigDict(extra="forbid"),
        **filter_fields,
    )

    return FilterSchema


# Predefined common schema sets
CATALOG_SCHEMAS = {
    "BusinessType": create_catalog_schemas("BusinessType"),
    "BusinessCategory": create_catalog_schemas("BusinessCategory"),
    "SectorTemplate": create_catalog_schemas(
        "SectorTemplate",
        extra_fields={
            "template_config": (dict[str, Any] | None, Field(default_factory=dict)),
            "config_version": (int | None, Field(None)),
        },
    ),
    "Language": create_catalog_schemas("Language", include_tenant=False),
    "Currency": create_catalog_schemas(
        "Currency", include_tenant=False, extra_fields={"symbol": (str, Field(..., max_length=5))}
    ),
    "Country": create_catalog_schemas("Country", include_tenant=False),
    "Weekday": create_catalog_schemas(
        "Weekday",
        include_tenant=False,
        extra_fields={
            "key": (str, Field(..., max_length=20)),
            "order": (int, Field(...)),
        },
    ),
}


def get_catalog_schemas(model_name: str) -> dict[str, type[BaseModel]]:
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
