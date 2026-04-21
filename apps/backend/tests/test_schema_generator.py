"""
Tests for schema generator utility.
"""

import pytest
from typing import Dict, Type

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.utils.schema_generator import (
    create_catalog_schemas,
    create_paginated_response_schema,
    create_filter_schema,
    get_catalog_schemas,
    CATALOG_SCHEMAS,
)


class TestCreateCatalogSchemas:
    """Test create_catalog_schemas function."""
    
    def test_creates_all_four_schema_types(self):
        """Test function creates Base, Create, Update, Response schemas."""
        schemas = create_catalog_schemas("TestEntity")
        
        assert "Base" in schemas
        assert "Create" in schemas
        assert "Update" in schemas
        assert "Response" in schemas
    
    def test_base_schema_has_catalog_fields(self):
        """Test Base schema has all catalog fields."""
        schemas = create_catalog_schemas("TestEntity")
        BaseSchema = schemas["Base"]
        
        # Test field definitions exist
        assert hasattr(BaseSchema, 'model_fields')
        
        # Create instance to test fields
        instance = BaseSchema(name="Test", code="TEST", is_active=True)
        
        assert instance.name == "Test"
        assert instance.code == "TEST"
        assert instance.is_active is True
        assert instance.description is None  # Should be optional
    
    def test_create_schema_inherits_from_base(self):
        """Test Create schema inherits from Base."""
        schemas = create_catalog_schemas("TestEntity")
        BaseSchema = schemas["Base"]
        CreateSchema = schemas["Create"]
        
        # Create should inherit from Base
        assert issubclass(CreateSchema, BaseSchema)
        
        # Should have same fields as Base
        base_fields = set(BaseSchema.model_fields.keys())
        create_fields = set(CreateSchema.model_fields.keys())
        assert base_fields == create_fields
    
    def test_update_schema_has_optional_fields(self):
        """Test Update schema has all fields optional."""
        schemas = create_catalog_schemas("TestEntity")
        UpdateSchema = schemas["Update"]
        
        # Create instance with no fields
        instance = UpdateSchema()
        
        # All fields should be optional (no validation errors)
        assert instance.name is None
        assert instance.code is None
        assert instance.description is None
        assert instance.is_active is None
    
    def test_response_schema_has_id_and_timestamps(self):
        """Test Response schema includes id and timestamps."""
        schemas = create_catalog_schemas("TestEntity")
        ResponseSchema = schemas["Response"]
        
        # Test field existence
        fields = ResponseSchema.model_fields
        assert "id" in fields
        assert "created_at" in fields
        assert "updated_at" in fields
        assert "name" in fields  # Should inherit base fields
    
    def test_extra_fields_are_included(self):
        """Test extra fields are included in all schemas."""
        extra_fields = {
            "custom_field": ("str", Field(...)),
            "optional_field": ("int | None", Field(None)),
        }
        
        schemas = create_catalog_schemas("TestEntity", extra_fields=extra_fields)
        
        for schema_type, schema_class in schemas.items():
            fields = schema_class.model_fields
            assert "custom_field" in fields
            assert "optional_field" in fields
    
    def test_include_tenant_false_excludes_tenant_id(self):
        """Test include_tenant=False excludes tenant_id from schemas."""
        schemas = create_catalog_schemas("TestEntity", include_tenant=False)
        BaseSchema = schemas["Base"]
        
        # Should not have tenant_id field
        fields = BaseSchema.model_fields
        assert "tenant_id" not in fields
    
    def test_include_tenant_true_includes_tenant_id(self):
        """Test include_tenant=True includes tenant_id in schemas."""
        schemas = create_catalog_schemas("TestEntity", include_tenant=True)
        BaseSchema = schemas["Base"]
        
        # Should have tenant_id field
        fields = BaseSchema.model_fields
        assert "tenant_id" in fields


class TestCreatePaginatedResponseSchema:
    """Test create_paginated_response_schema function."""
    
    def test_creates_paginated_response_schema(self):
        """Test function creates proper paginated response schema."""
        class TestItem(BaseModel):
            id: str
            name: str
        
        ResponseSchema = create_paginated_response_schema(TestItem)
        
        # Should have required fields
        fields = ResponseSchema.model_fields
        assert "items" in fields
        assert "total" in fields
        assert "page" in fields
        assert "per_page" in fields
        assert "pages" in fields
        
        # Should be list of TestItem
        assert ResponseSchema.model_fields["items"].annotation == list[TestItem]
    
    def test_response_schema_validation(self):
        """Test response schema validates correctly."""
        class TestItem(BaseModel):
            id: str
            name: str
        
        ResponseSchema = create_paginated_response_schema(TestItem)
        
        # Valid data should pass
        valid_data = {
            "items": [{"id": "1", "name": "Test"}],
            "total": 1,
            "page": 1,
            "per_page": 20,
            "pages": 1
        }
        
        instance = ResponseSchema(**valid_data)
        assert len(instance.items) == 1
        assert instance.items[0].name == "Test"
        assert instance.total == 1


class TestCreateFilterSchema:
    """Test create_filter_schema function."""
    
    def test_creates_filter_schema_with_defaults(self):
        """Test function creates schema with default filter fields."""
        FilterSchema = create_filter_schema("TestEntity")
        
        # Should have default fields
        fields = FilterSchema.model_fields
        assert "page" in fields
        assert "per_page" in fields
        assert "search" in fields
    
    def test_includes_searchable_fields(self):
        """Test searchable fields are included as _contains filters."""
        FilterSchema = create_filter_schema(
            "TestEntity",
            searchable_fields=["name", "code"]
        )
        
        fields = FilterSchema.model_fields
        assert "name_contains" in fields
        assert "code_contains" in fields
    
    def test_includes_filterable_fields(self):
        """Test filterable fields are included directly."""
        FilterSchema = create_filter_schema(
            "TestEntity",
            filterable_fields={"is_active": bool, "category": str}
        )
        
        fields = FilterSchema.model_fields
        assert "is_active" in fields
        assert "category" in fields


class TestGetCatalogSchemas:
    """Test get_catalog_schemas function."""
    
    def test_returns_existing_catalog_schemas(self):
        """Test function returns predefined schemas for known catalogs."""
        schemas = get_catalog_schemas("BusinessType")
        
        # Should return all four schema types
        assert "Base" in schemas
        assert "Create" in schemas
        assert "Update" in schemas
        assert "Response" in schemas
    
    def test_unknown_catalog_creates_new_schemas(self):
        """Test function creates new schemas for unknown catalogs."""
        schemas = get_catalog_schemas("UnknownCatalog")
        
        # Should still return all four schema types
        assert "Base" in schemas
        assert "Create" in schemas
        assert "Update" in schemas
        assert "Response" in schemas
    
    def test_business_type_schemas_have_currency_symbol(self):
        """Test BusinessType schemas have currency-specific fields."""
        schemas = get_catalog_schemas("Currency")
        BaseSchema = schemas["Base"]
        
        # Currency should have symbol field
        fields = BaseSchema.model_fields
        assert "symbol" in fields
    
    def test_weekday_schemas_have_key_and_order(self):
        """Test Weekday schemas have specific fields."""
        schemas = get_catalog_schemas("Weekday")
        BaseSchema = schemas["Base"]
        
        # Weekday should have key and order fields
        fields = BaseSchema.model_fields
        assert "key" in fields
        assert "order" in fields


class TestCatalogSchemasConstants:
    """Test CATALOG_SCHEMAS constant."""
    
    def test_catalog_schemas_is_dict(self):
        """Test CATALOG_SCHEMAS is a dictionary."""
        assert isinstance(CATALOG_SCHEMAS, dict)
    
    def test_contains_expected_catalogs(self):
        """Test CATALOG_SCHEMAS contains expected catalog types."""
        expected_catalogs = [
            "BusinessType",
            "BusinessCategory", 
            "SectorTemplate",
            "Language",
            "Currency",
            "Country",
            "Weekday"
        ]
        
        for catalog in expected_catalogs:
            assert catalog in CATALOG_SCHEMAS
    
    def test_each_catalog_has_all_schema_types(self):
        """Test each catalog has all four schema types."""
        for catalog_name, schemas in CATALOG_SCHEMAS.items():
            assert isinstance(schemas, dict)
            assert "Base" in schemas
            assert "Create" in schemas
            assert "Update" in schemas
            assert "Response" in schemas
            
            # All should be BaseModel subclasses
            for schema_type, schema_class in schemas.items():
                assert issubclass(schema_class, BaseModel)


class TestSchemaValidation:
    """Test schema validation behavior."""
    
    def test_base_schema_name_required(self):
        """Test Base schema requires name field."""
        schemas = create_catalog_schemas("TestEntity")
        BaseSchema = schemas["Base"]
        
        # Should fail validation without name
        with pytest.raises(Exception):  # Pydantic ValidationError
            BaseSchema()
        
        # Should pass with name
        instance = BaseSchema(name="Test")
        assert instance.name == "Test"
    
    def test_base_schema_name_length_validation(self):
        """Test Base schema validates name length."""
        schemas = create_catalog_schemas("TestEntity")
        BaseSchema = schemas["Base"]
        
        # Should fail with name too long
        with pytest.raises(Exception):
            BaseSchema(name="x" * 101)  # 101 characters, max is 100
        
        # Should pass with valid length
        instance = BaseSchema(name="x" * 100)  # 100 characters
        assert len(instance.name) == 100
    
    def test_base_schema_code_length_validation(self):
        """Test Base schema validates code length."""
        schemas = create_catalog_schemas("TestEntity")
        BaseSchema = schemas["Base"]
        
        # Should fail with code too long
        with pytest.raises(Exception):
            BaseSchema(name="Test", code="x" * 51)  # 51 characters, max is 50
        
        # Should pass with valid length
        instance = BaseSchema(name="Test", code="x" * 50)  # 50 characters
        assert len(instance.code) == 50
    
    def test_update_schema_all_fields_optional(self):
        """Test Update schema accepts all fields optional."""
        schemas = create_catalog_schemas("TestEntity")
        UpdateSchema = schemas["Update"]
        
        # Should create empty instance
        instance = UpdateSchema()
        assert instance.name is None
        assert instance.code is None
        assert instance.description is None
        assert instance.is_active is None
        
        # Should update individual fields
        instance2 = UpdateSchema(name="Updated")
        assert instance2.name == "Updated"
        assert instance2.code is None  # Other fields should remain None
