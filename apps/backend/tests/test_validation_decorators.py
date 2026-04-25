"""
Tests for validation decorators.
"""

import pytest
from uuid import UUID, uuid4
from unittest.mock import ANY, Mock, patch

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.decorators.validation import (
    validate_uuid,
    extract_tenant_id,
    validate_resource_exists,
    handle_not_found,
    validate_pagination_params,
    tenant_required,
)


class TestValidateUUID:
    """Test validate_uuid function."""

    def test_valid_uuid_string(self):
        """Test valid UUID string is converted to UUID object."""
        uuid_str = str(uuid4())
        result = validate_uuid(uuid_str, "test_id")

        assert isinstance(result, UUID)
        assert str(result) == uuid_str

    def test_invalid_uuid_string_raises_400(self):
        """Test invalid UUID string raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("invalid-uuid", "test_id")

        assert exc_info.value.status_code == 400
        assert "Invalid test_id" in exc_info.value.detail

    def test_none_uuid_raises_400(self):
        """Test None UUID raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid(None, "test_id")

        assert exc_info.value.status_code == 400
        assert "Invalid test_id" in exc_info.value.detail

    def test_custom_field_name_in_error(self):
        """Test custom field name appears in error message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_uuid("invalid", "custom_field")

        assert "Invalid custom_field" in exc_info.value.detail


class TestExtractTenantId:
    """Test extract_tenant_id function."""

    def test_extract_tenant_from_claims(self):
        """Test tenant extraction from access_claims."""
        mock_request = Mock()
        mock_request.state.access_claims = {"tenant_id": "tenant-123"}

        result = extract_tenant_id(mock_request)
        assert result == "tenant-123"

    def test_extract_tenant_from_session(self):
        """Test tenant extraction from session when claims missing."""
        mock_request = Mock()
        mock_request.state.access_claims = {}
        mock_request.state.session = {"tenant_id": "tenant-456"}

        result = extract_tenant_id(mock_request)
        assert result == "tenant-456"

    def test_no_tenant_raises_400(self):
        """Test missing tenant raises HTTPException."""
        mock_request = Mock()
        mock_request.state.access_claims = {}
        mock_request.state.session = {}

        with pytest.raises(HTTPException) as exc_info:
            extract_tenant_id(mock_request)

        assert exc_info.value.status_code == 400
        assert "Tenant not found" in exc_info.value.detail


class TestValidateResourceExists:
    """Test validate_resource_exists decorator."""

    def setup_method(self):
        """Setup mock get_resource function."""
        self.mock_get_resource = Mock()
        self.tenant_id = "tenant-123"
        self.resource_id = "resource-456"

    def test_resource_exists_calls_get_resource(self):
        """Test decorator calls get_resource function with correct parameters."""
        decorator = validate_resource_exists(self.mock_get_resource, "TestResource")

        @decorator
        def test_endpoint(db, tenant_id, resource_id, validated_testresource):
            return validated_testresource

        # Mock successful resource retrieval
        mock_resource = Mock()
        self.mock_get_resource.return_value = mock_resource

        result = test_endpoint(
            db=Mock(),
            tenant_id=self.tenant_id,
            resource_id=self.resource_id
        )

        # Verify get_resource was called correctly
        self.mock_get_resource.assert_called_once_with(ANY, self.tenant_id, self.resource_id)
        assert result == mock_resource

    def test_resource_not_found_raises_404(self):
        """Test decorator raises 404 when resource not found."""
        decorator = validate_resource_exists(self.mock_get_resource, "TestResource")

        @decorator
        def test_endpoint(db, tenant_id, resource_id, validated_testresource):
            return validated_testresource

        # Mock resource not found
        self.mock_get_resource.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(
                db=Mock(),
                tenant_id=self.tenant_id,
                resource_id=self.resource_id
            )

        assert exc_info.value.status_code == 404
        assert "TestResource not found" in exc_info.value.detail

    def test_missing_parameters_raises_500(self):
        """Test decorator raises 500 when required parameters missing."""
        decorator = validate_resource_exists(self.mock_get_resource, "TestResource")

        @decorator
        def test_endpoint(db, tenant_id):
            return "success"

        with pytest.raises(HTTPException) as exc_info:
            test_endpoint(db=Mock(), tenant_id=self.tenant_id)

        assert exc_info.value.status_code == 500
        assert "Missing required parameters" in exc_info.value.detail


class TestHandleNotFound:
    """Test handle_not_found decorator."""

    def test_value_error_with_not_found_converts_to_404(self):
        """Test ValueError with 'not found' converts to HTTP 404."""
        decorator = handle_not_found("TestResource")

        @decorator
        def test_function():
            raise ValueError("TestResource not found")

        with pytest.raises(HTTPException) as exc_info:
            test_function()

        assert exc_info.value.status_code == 404
        assert "TestResource not found" in exc_info.value.detail

    def test_other_errors_pass_through(self):
        """Test other errors pass through unchanged."""
        decorator = handle_not_found("TestResource")

        @decorator
        def test_function():
            raise ValueError("Some other error")

        with pytest.raises(ValueError) as exc_info:
            test_function()

        assert str(exc_info.value) == "Some other error"

    def test_non_value_errors_pass_through(self):
        """Test non-ValueError exceptions pass through unchanged."""
        decorator = handle_not_found("TestResource")

        @decorator
        def test_function():
            raise RuntimeError("Runtime error")

        with pytest.raises(RuntimeError):
            test_function()


class TestValidatePaginationParams:
    """Test validate_pagination_params decorator."""

    def test_valid_pagination_params_pass_through(self):
        """Test valid pagination parameters pass through unchanged."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page=2, per_page=50)
        assert result == (2, 50)

    def test_invalid_page_defaults_to_1(self):
        """Test invalid page defaults to 1."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page=0, per_page=20)
        assert result == (1, 20)

    def test_negative_page_defaults_to_1(self):
        """Test negative page defaults to 1."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page=-5, per_page=20)
        assert result == (1, 20)

    def test_per_page_limited_to_1000(self):
        """Test per_page is limited to maximum of 1000."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page=1, per_page=2000)
        assert result == (1, 1000)

    def test_per_page_minimum_of_1(self):
        """Test per_page minimum of 1."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page=1, per_page=0)
        assert result == (1, 1)

    def test_string_parameters_converted_to_int(self):
        """Test string parameters are converted to int."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page="3", per_page="25")
        assert result == (3, 25)

    def test_invalid_string_defaults(self):
        """Test invalid string parameters use defaults."""
        decorator = validate_pagination_params

        @decorator
        def test_function(page, per_page):
            return page, per_page

        result = test_function(page="invalid", per_page="invalid")
        assert result == (1, 20)


class TestTenantRequired:
    """Test tenant_required decorator."""

    @patch('app.decorators.validation.extract_tenant_id')
    def test_tenant_extracted_and_added_to_kwargs(self, mock_extract):
        """Test tenant is extracted and added to kwargs."""
        mock_extract.return_value = "tenant-123"
        mock_request = Mock()

        decorator = tenant_required

        @decorator
        def test_function(request, other_param, tenant_id=None):
            return other_param, tenant_id

        result = test_function(request=mock_request, other_param="test")

        # Verify extract_tenant_id was called
        mock_extract.assert_called_once_with(mock_request)
        assert result == ("test", "tenant-123")

    def test_missing_request_raises_500(self):
        """Test missing request parameter raises 500."""
        decorator = tenant_required

        @decorator
        def test_function(other_param):
            return other_param

        with pytest.raises(HTTPException) as exc_info:
            test_function(other_param="test")

        assert exc_info.value.status_code == 500
        assert "Request object not found" in exc_info.value.detail
