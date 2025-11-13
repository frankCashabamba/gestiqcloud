"""Validators for product imports."""

from typing import Any


def validate_product(data: dict[str, Any]) -> list[str]:
    """Validate product import data.

    Args:
        data: Product data dict with keys:
            - name/producto: Product name (required)
            - precio/price: Unit price (required, must be >= 0)
            - cantidad/quantity/stock: Stock quantity (optional, default 0)
            - categoria/category: Category name (optional)

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Required: product name
    name = str(data.get("name") or data.get("producto") or "").strip()
    if not name:
        errors.append("Falta nombre de producto")
    elif len(name) > 255:
        errors.append("Nombre de producto demasiado largo (máx 255 caracteres)")

    # Required: price (must be numeric and >= 0)
    price = data.get("precio") or data.get("price")
    if price is None or price == "":
        errors.append("Falta precio de producto")
    else:
        try:
            price_val = float(price)
            if price_val < 0:
                errors.append("Precio no puede ser negativo")
        except (ValueError, TypeError):
            errors.append(f"Precio inválido: '{price}'")

    # Optional: quantity/stock (must be numeric if provided)
    quantity = data.get("cantidad") or data.get("quantity") or data.get("stock")
    if quantity is not None and quantity != "":
        try:
            qty_val = float(quantity)
            if qty_val < 0:
                errors.append("Cantidad no puede ser negativa")
        except (ValueError, TypeError):
            errors.append(f"Cantidad inválida: '{quantity}'")

    # Optional: category name validation
    category = str(data.get("categoria") or data.get("category") or "").strip()
    if category and len(category) > 200:
        errors.append("Nombre de categoría demasiado largo (máx 200 caracteres)")

    # Optional: SKU validation
    sku = data.get("sku")
    if sku and len(str(sku)) > 100:
        errors.append("SKU demasiado largo (máx 100 caracteres)")

    return errors


def validate_products_batch(items: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Validate a batch of products.

    Args:
        items: List of product data dicts

    Returns:
        Dict mapping item index to list of errors
    """
    errors_by_index = {}

    for idx, item in enumerate(items):
        item_errors = validate_product(item)
        if item_errors:
            errors_by_index[idx] = item_errors

    return errors_by_index
