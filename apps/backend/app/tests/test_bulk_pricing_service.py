"""Tests for bulk pricing service."""

import pytest

from app.services.bulk_pricing_service import BulkPricingService


class TestGetBulkConfigForProduct:
    """Tests for get_bulk_config_for_product method."""

    def test_find_existing_product(self):
        """Test finding bulk config for existing product."""
        items = [
            {'product_id': 'prod-1', 'quantity': 6, 'unit_price': 1.00},
            {'product_id': 'prod-2', 'quantity': 12, 'unit_price': 1.80},
        ]
        
        result = BulkPricingService.get_bulk_config_for_product('prod-1', items)
        
        assert result is not None
        assert result['product_id'] == 'prod-1'
        assert result['quantity'] == 6
        assert result['unit_price'] == 1.00

    def test_product_not_found(self):
        """Test when product is not in list."""
        items = [
            {'product_id': 'prod-1', 'quantity': 6, 'unit_price': 1.00},
        ]
        
        result = BulkPricingService.get_bulk_config_for_product('prod-3', items)
        
        assert result is None

    def test_empty_list(self):
        """Test with empty list."""
        result = BulkPricingService.get_bulk_config_for_product('prod-1', [])
        
        assert result is None

    def test_none_list(self):
        """Test with None list."""
        result = BulkPricingService.get_bulk_config_for_product('prod-1', None)
        
        assert result is None

    def test_malformed_list(self):
        """Test with malformed list."""
        items = ['not a dict', 123]
        
        result = BulkPricingService.get_bulk_config_for_product('prod-1', items)
        
        assert result is None


class TestCalculateBulkPrice:
    """Tests for calculate_bulk_price method."""

    def test_no_bulk_config(self):
        """Test calculation without bulk pricing config."""
        result = BulkPricingService.calculate_bulk_price(
            quantity=10,
            bulk_config=None,
            unit_price=0.5,
        )
        
        assert result['uses_bulk_pricing'] is False
        assert result['quantity'] == 10
        assert result['total_price'] == 5.0
        assert result['unit_price_effective'] == 0.5

    def test_complete_sets_only(self):
        """Test calculation with complete sets only."""
        bulk_config = {'quantity': 6, 'unit_price': 1.00}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=18,
            bulk_config=bulk_config,
        )
        
        assert result['uses_bulk_pricing'] is True
        assert result['calculation']['num_complete_sets'] == 3
        assert result['calculation']['remaining_units'] == 0
        assert result['total_from_sets'] == 3.00
        assert result['total_from_remaining'] == 0.0
        assert result['total_price'] == 3.00
        assert result['unit_price_effective'] == pytest.approx(0.1667, abs=0.001)

    def test_sets_with_remainder(self):
        """Test calculation with complete sets and remainder."""
        bulk_config = {'quantity': 6, 'unit_price': 1.00}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=20,
            bulk_config=bulk_config,
        )
        
        assert result['uses_bulk_pricing'] is True
        assert result['calculation']['num_complete_sets'] == 3
        assert result['calculation']['remaining_units'] == 2
        assert result['total_from_sets'] == 3.00
        assert result['total_from_remaining'] == pytest.approx(0.33, abs=0.01)
        assert result['total_price'] == pytest.approx(3.33, abs=0.01)

    def test_quantity_less_than_set_size(self):
        """Test calculation when quantity is less than set size."""
        bulk_config = {'quantity': 6, 'unit_price': 1.00}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=3,
            bulk_config=bulk_config,
        )
        
        assert result['uses_bulk_pricing'] is True
        assert result['calculation']['num_complete_sets'] == 0
        assert result['calculation']['remaining_units'] == 3
        assert result['total_from_sets'] == 0.0
        assert result['total_from_remaining'] == pytest.approx(0.50, abs=0.01)
        assert result['total_price'] == pytest.approx(0.50, abs=0.01)

    def test_invalid_config_zero_quantity(self):
        """Test with invalid config (zero quantity)."""
        bulk_config = {'quantity': 0, 'unit_price': 1.00}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=10,
            bulk_config=bulk_config,
            unit_price=0.5,
        )
        
        assert result['uses_bulk_pricing'] is False
        assert result['total_price'] == 5.0

    def test_invalid_config_negative_price(self):
        """Test with invalid config (negative price)."""
        bulk_config = {'quantity': 6, 'unit_price': -1.00}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=10,
            bulk_config=bulk_config,
            unit_price=0.5,
        )
        
        assert result['uses_bulk_pricing'] is False

    def test_invalid_config_malformed(self):
        """Test with malformed config."""
        bulk_config = {'quantity': 'six', 'unit_price': 'one'}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=10,
            bulk_config=bulk_config,
            unit_price=0.5,
        )
        
        assert result['uses_bulk_pricing'] is False

    def test_quantity_one(self):
        """Test with single unit quantity."""
        bulk_config = {'quantity': 1, 'unit_price': 0.50}
        
        result = BulkPricingService.calculate_bulk_price(
            quantity=5,
            bulk_config=bulk_config,
        )
        
        assert result['uses_bulk_pricing'] is True
        assert result['calculation']['num_complete_sets'] == 5
        assert result['calculation']['remaining_units'] == 0
        assert result['total_price'] == 2.50
        assert result['unit_price_effective'] == 0.50


class TestValidateBulkConfig:
    """Tests for validate_bulk_config method."""

    def test_valid_config(self):
        """Test validation of valid config."""
        bulk_config = {'quantity': 6, 'unit_price': 1.00}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is True
        assert error is None

    def test_none_config(self):
        """Test validation of None config."""
        is_valid, error = BulkPricingService.validate_bulk_config(None)
        
        assert is_valid is True
        assert error is None

    def test_missing_quantity(self):
        """Test validation with missing quantity."""
        bulk_config = {'unit_price': 1.00}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is False
        assert 'Missing required fields' in error

    def test_missing_price(self):
        """Test validation with missing price."""
        bulk_config = {'quantity': 6}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is False
        assert 'Missing required fields' in error

    def test_zero_quantity(self):
        """Test validation with zero quantity."""
        bulk_config = {'quantity': 0, 'unit_price': 1.00}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is False
        assert 'greater than 0' in error

    def test_negative_price(self):
        """Test validation with negative price."""
        bulk_config = {'quantity': 6, 'unit_price': -1.00}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is False
        assert 'negative' in error

    def test_invalid_data_types(self):
        """Test validation with invalid data types."""
        bulk_config = {'quantity': 'six', 'unit_price': [1, 2, 3]}
        
        is_valid, error = BulkPricingService.validate_bulk_config(bulk_config)
        
        assert is_valid is False


class TestFormatBulkPricingDisplay:
    """Tests for format_bulk_pricing_display method."""

    def test_valid_format(self):
        """Test formatting valid config."""
        bulk_config = {'quantity': 6, 'unit_price': 1.00}
        
        result = BulkPricingService.format_bulk_pricing_display(bulk_config)
        
        assert result == "6 units for $1.00"

    def test_none_config(self):
        """Test formatting None config."""
        result = BulkPricingService.format_bulk_pricing_display(None)
        
        assert result == ""

    def test_empty_config(self):
        """Test formatting empty config."""
        result = BulkPricingService.format_bulk_pricing_display({})
        
        assert result == ""

    def test_decimal_price(self):
        """Test formatting with decimal price."""
        bulk_config = {'quantity': 5, 'unit_price': 1.50}
        
        result = BulkPricingService.format_bulk_pricing_display(bulk_config)
        
        assert result == "5 units for $1.50"

    def test_malformed_config(self):
        """Test formatting malformed config."""
        bulk_config = {'quantity': 'six', 'unit_price': 'one'}
        
        result = BulkPricingService.format_bulk_pricing_display(bulk_config)
        
        assert result == ""
