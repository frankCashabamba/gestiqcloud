"""
Tests for BaseCatalogModel and related utilities.
"""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import BaseCatalogModel, BaseCatalogModelWithoutTenant
from app.models.company.company import BusinessType, BusinessCategory, Language, Currency


class TestBaseCatalogModel:
    """Test BaseCatalogModel functionality."""

    def setup_method(self):
        """Setup test database."""
        self.engine = create_engine("sqlite:///:memory:")
        BaseCatalogModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def test_business_type_inherits_catalog_fields(self):
        """Test BusinessType has all catalog fields."""
        # Create a business type
        business_type = BusinessType(
            tenant_id=uuid4(),
            code="TEST",
            name="Test Business Type",
            description="Test description",
            is_active=True
        )

        # Verify all catalog fields are present
        assert hasattr(business_type, 'id')
        assert hasattr(business_type, 'tenant_id')
        assert hasattr(business_type, 'code')
        assert hasattr(business_type, 'name')
        assert hasattr(business_type, 'description')
        assert hasattr(business_type, 'is_active')
        assert hasattr(business_type, 'created_at')
        assert hasattr(business_type, 'updated_at')

    def test_business_category_inherits_catalog_fields(self):
        """Test BusinessCategory has all catalog fields."""
        business_category = BusinessCategory(
            name="Test Category",
            code="CAT_TEST",
            is_active=True
        )

        # Verify catalog fields
        assert business_category.name == "Test Category"
        assert business_category.code == "CAT_TEST"
        assert business_category.is_active is True
        assert not hasattr(business_category, "tenant_id")

    def test_active_property_backward_compatibility(self):
        """Test active property works for backward compatibility."""
        business_type = BusinessType(
            tenant_id=uuid4(),
            name="Test",
            is_active=True
        )

        # Test getter
        assert business_type.active is True
        assert business_type.is_active is True

        # Test setter
        business_type.active = False
        assert business_type.active is False
        assert business_type.is_active is False

    def test_timestamps_are_set_automatically(self):
        """Test timestamps are set automatically."""
        business_type = BusinessType(
            tenant_id=uuid4(),
            name="Test",
            is_active=True
        )

        self.session.add(business_type)
        self.session.flush()

        # Timestamps should be datetime objects
        assert isinstance(business_type.created_at, datetime)
        assert isinstance(business_type.updated_at, datetime)
        assert business_type.created_at.tzinfo == UTC
        assert business_type.updated_at.tzinfo == UTC


class TestBaseCatalogModelWithoutTenant:
    """Test BaseCatalogModelWithoutTenant functionality."""

    def setup_method(self):
        """Setup test database."""
        self.engine = create_engine("sqlite:///:memory:")
        BaseCatalogModelWithoutTenant.metadata.create_all(self.engine)
        self.session = Session(self.engine)

    def test_language_without_tenant(self):
        """Test Language model doesn't have tenant_id."""
        language = Language(
            code="en",
            name="English",
            is_active=True
        )

        # Should not have tenant_id
        assert not hasattr(language, 'tenant_id')

        # Should have other catalog fields
        assert hasattr(language, 'id')
        assert hasattr(language, 'code')
        assert hasattr(language, 'name')
        assert hasattr(language, 'is_active')
        assert hasattr(language, 'created_at')
        assert hasattr(language, 'updated_at')

    def test_currency_without_tenant(self):
        """Test Currency model has additional fields but no tenant_id."""
        currency = Currency(
            code="USD",
            name="US Dollar",
            symbol="$",
            is_active=True
        )

        # Should not have tenant_id
        assert not hasattr(currency, 'tenant_id')

        # Should have symbol field
        assert currency.symbol == "$"

        # Should have other catalog fields
        assert hasattr(currency, 'id')
        assert hasattr(currency, 'code')
        assert hasattr(currency, 'name')
        assert hasattr(currency, 'is_active')

    def test_active_property_works_without_tenant(self):
        """Test active property works without tenant models."""
        language = Language(
            code="es",
            name="Spanish",
            is_active=False
        )

        # Test backward compatibility
        assert language.active is False
        assert language.is_active is False

        # Test setter
        language.active = True
        assert language.active is True
        assert language.is_active is True


class TestCatalogModelInheritance:
    """Test inheritance patterns work correctly."""

    def test_business_type_inheritance(self):
        """Test BusinessType inheritance from BaseCatalogModel."""
        # Check that BusinessType inherits from BaseCatalogModel
        assert issubclass(BusinessType, BaseCatalogModel)

        # Check that it has the right table name
        assert BusinessType.__tablename__ == "business_types"

    def test_language_inheritance(self):
        """Test Language inheritance from BaseCatalogModelWithoutTenant."""
        # Check that Language inherits from BaseCatalogModelWithoutTenant
        assert issubclass(Language, BaseCatalogModelWithoutTenant)

        # Check that it has the right table name
        assert Language.__tablename__ == "languages"

    def test_model_metadata_includes_all_fields(self):
        """Test model metadata includes all catalog fields."""
        # Check BusinessType table columns
        business_type_columns = BusinessType.__table__.columns.keys()
        expected_catalog_columns = [
            'id', 'tenant_id', 'code', 'name', 'description',
            'is_active', 'created_at', 'updated_at'
        ]

        for column in expected_catalog_columns:
            assert column in business_type_columns, f"Missing column: {column}"
