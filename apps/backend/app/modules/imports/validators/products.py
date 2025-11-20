"""Product validators for imports"""

from typing import Any


def validate_product(product_data: dict[str, Any]) -> list[dict]:
    """
    Validates a product row during import.

    Args:
        product_data: Product data dictionary

    Returns:
        List of error dictionaries with 'field' and 'msg' keys
    """
    errors: list[dict] = []

    # Validate required fields
    if not product_data.get("name"):
        errors.append({"field": "name", "msg": "required"})

    if product_data.get("sku") is not None:
        sku = str(product_data.get("sku", "")).strip()
        if not sku:
            errors.append({"field": "sku", "msg": "cannot be empty"})

    # Validate price if provided
    if product_data.get("price") is not None:
        try:
            price = float(product_data.get("price"))
            if price < 0:
                errors.append({"field": "price", "msg": "cannot be negative"})
        except (ValueError, TypeError):
            errors.append({"field": "price", "msg": "must be a valid number"})

    # Validate cost_price if provided
    if product_data.get("cost_price") is not None:
        try:
            cost_price = float(product_data.get("cost_price"))
            if cost_price < 0:
                errors.append({"field": "cost_price", "msg": "cannot be negative"})
        except (ValueError, TypeError):
            errors.append({"field": "cost_price", "msg": "must be a valid number"})

    # Validate tax_rate if provided
    if product_data.get("tax_rate") is not None:
        try:
            tax_rate = float(product_data.get("tax_rate"))
            if tax_rate < 0 or tax_rate > 100:
                errors.append({"field": "tax_rate", "msg": "must be between 0 and 100"})
        except (ValueError, TypeError):
            errors.append({"field": "tax_rate", "msg": "must be a valid number"})

    # Validate stock if provided
    if product_data.get("stock") is not None:
        try:
            stock = float(product_data.get("stock"))
            if stock < 0:
                errors.append({"field": "stock", "msg": "cannot be negative"})
        except (ValueError, TypeError):
            errors.append({"field": "stock", "msg": "must be a valid number"})

    return errors
