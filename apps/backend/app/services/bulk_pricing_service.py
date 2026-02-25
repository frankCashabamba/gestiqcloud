"""Service for handling bulk pricing calculations in POS."""


class BulkPricingService:
    """Service to handle bulk pricing operations for products.

    Useful for bakeries and similar businesses where items are sold by quantity.
    Example: 6 tapapados (pastries) for $1.00
    """

    @staticmethod
    def get_bulk_config_for_product(
        product_id: str,
        bulk_pricing_items: list | None,
    ) -> dict | None:
        """Get bulk pricing config for a specific product.

        Args:
            product_id: Product ID to look up
            bulk_pricing_items: List of bulk pricing configs

        Returns:
            Bulk pricing config or None if not found
        """
        if not bulk_pricing_items:
            return None

        try:
            for item in bulk_pricing_items:
                if item.get("product_id") == product_id:
                    return item
        except (TypeError, AttributeError):
            pass

        return None

    @staticmethod
    def calculate_bulk_price(
        quantity: int,
        bulk_config: dict | None,
        unit_price: float = 0.0,
    ) -> dict:
        """Calculate pricing based on bulk configuration.

        Args:
            quantity: Total number of units to purchase
            bulk_config: Configuration with 'quantity' and 'unit_price' keys
            unit_price: Individual unit price (fallback if bulk not applicable)

        Returns:
            Dictionary with pricing breakdown

        Example:
            bulk_config = {'quantity': 6, 'unit_price': 1.00}
            result = BulkPricingService.calculate_bulk_price(18, bulk_config)
            # Returns: {
            #     'uses_bulk_pricing': True,
            #     'num_sets': 3,
            #     'remaining_units': 0,
            #     'total_from_sets': 3.00,
            #     'total_from_remaining': 0.00,
            #     'total_price': 3.00,
            #     'unit_price_effective': 0.1667
            # }
        """
        if not bulk_config:
            return {
                "uses_bulk_pricing": False,
                "quantity": quantity,
                "total_price": quantity * unit_price,
                "unit_price_effective": unit_price,
            }

        try:
            required_quantity = int(bulk_config.get("quantity", 0))
            total_price_per_set = float(bulk_config.get("unit_price", 0))

            if required_quantity <= 0 or total_price_per_set < 0:
                # Invalid config, fall back to standard pricing
                return {
                    "uses_bulk_pricing": False,
                    "quantity": quantity,
                    "total_price": quantity * unit_price,
                    "unit_price_effective": unit_price,
                }

            # Calculate how many sets fit in the quantity
            num_sets = quantity // required_quantity
            remaining_units = quantity % required_quantity

            # Calculate prices
            total_from_sets = num_sets * total_price_per_set
            price_per_unit = total_price_per_set / required_quantity
            total_from_remaining = remaining_units * price_per_unit

            return {
                "uses_bulk_pricing": True,
                "quantity": quantity,
                "bulk_config": {
                    "set_size": required_quantity,
                    "set_price": total_price_per_set,
                },
                "calculation": {
                    "num_complete_sets": num_sets,
                    "remaining_units": remaining_units,
                    "price_per_unit": round(price_per_unit, 4),
                },
                "total_from_sets": round(total_from_sets, 2),
                "total_from_remaining": round(total_from_remaining, 2),
                "total_price": round(total_from_sets + total_from_remaining, 2),
                "unit_price_effective": round(price_per_unit, 4),
            }
        except (TypeError, ValueError, KeyError):
            # Invalid config, fall back to standard pricing
            return {
                "uses_bulk_pricing": False,
                "quantity": quantity,
                "total_price": quantity * unit_price,
                "unit_price_effective": unit_price,
            }

    @staticmethod
    def validate_bulk_config(bulk_config: dict | None) -> tuple[bool, str | None]:
        """Validate bulk pricing configuration.

        Args:
            bulk_config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not bulk_config:
            return True, None

        try:
            quantity = bulk_config.get("quantity")
            unit_price = bulk_config.get("unit_price")

            if quantity is None or unit_price is None:
                return False, "Missing required fields: quantity and unit_price"

            quantity = int(quantity)
            unit_price = float(unit_price)

            if quantity <= 0:
                return False, "Quantity must be greater than 0"

            if unit_price < 0:
                return False, "Unit price cannot be negative"

            return True, None
        except (TypeError, ValueError):
            return False, "Invalid data types in bulk_config"

    @staticmethod
    def format_bulk_pricing_display(bulk_config: dict | None) -> str:
        """Format bulk pricing config for display.

        Args:
            bulk_config: Configuration to format

        Returns:
            Formatted string like "6 units for $1.00"
        """
        if not bulk_config:
            return ""

        try:
            quantity = bulk_config.get("quantity")
            unit_price = bulk_config.get("unit_price")

            if quantity and unit_price:
                return f"{quantity} units for ${float(unit_price):.2f}"

            return ""
        except (TypeError, ValueError):
            return ""
