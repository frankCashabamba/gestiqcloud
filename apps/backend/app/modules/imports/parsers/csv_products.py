"""CSV parser for products."""

import csv
from datetime import datetime
from typing import Any


def parse_csv_products(file_path: str) -> dict[str, Any]:
    """Parse CSV file with product data.

    Expects columns: name/producto/nombre, price/precio, quantity/cantidad,
    sku/codigo, category/categoria, description/descripcion

    Args:
        file_path: Path to CSV file

    Returns:
        Dict with 'products' list and metadata
    """
    products = []
    rows_processed = 0
    errors = []

    try:
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV file is empty or has no headers")

            for idx, row in enumerate(reader, start=1):
                rows_processed += 1

                # Normalize column names
                normalized_row = {k.strip().lower(): v for k, v in row.items()}

                # Extract canonical fields
                name = (
                    normalized_row.get("name")
                    or normalized_row.get("producto")
                    or normalized_row.get("nombre")
                    or normalized_row.get("product")
                )

                if not name or not str(name).strip():
                    continue

                product = {
                    "doc_type": "product",
                    "nombre": str(name).strip(),
                    "name": str(name).strip(),
                    "producto": str(name).strip(),
                    "price": _to_float(
                        normalized_row.get("price")
                        or normalized_row.get("precio")
                        or normalized_row.get("unit_price")
                    ),
                    "precio": _to_float(
                        normalized_row.get("price")
                        or normalized_row.get("precio")
                        or normalized_row.get("unit_price")
                    ),
                    "quantity": _to_float(
                        normalized_row.get("quantity")
                        or normalized_row.get("cantidad")
                        or normalized_row.get("stock")
                        or normalized_row.get("existencia")
                    ),
                    "cantidad": _to_float(
                        normalized_row.get("quantity")
                        or normalized_row.get("cantidad")
                        or normalized_row.get("stock")
                        or normalized_row.get("existencia")
                    ),
                    "stock": _to_float(
                        normalized_row.get("quantity")
                        or normalized_row.get("cantidad")
                        or normalized_row.get("stock")
                        or normalized_row.get("existencia")
                    ),
                    "category": (
                        normalized_row.get("category")
                        or normalized_row.get("categoria")
                        or normalized_row.get("category_name")
                        or "GENERAL"
                    ),
                    "categoria": (
                        normalized_row.get("category")
                        or normalized_row.get("categoria")
                        or normalized_row.get("category_name")
                        or "GENERAL"
                    ),
                    "source": "csv",
                    "_metadata": {
                        "parser": "csv_products",
                        "row_index": idx,
                        "imported_at": datetime.utcnow().isoformat(),
                    },
                }

                # Extract SKU if available
                sku = (
                    normalized_row.get("sku")
                    or normalized_row.get("codigo")
                    or normalized_row.get("code")
                    or normalized_row.get("reference")
                )
                if sku:
                    product["sku"] = str(sku).strip()

                # Extract description if available
                description = (
                    normalized_row.get("description")
                    or normalized_row.get("descripcion")
                    or normalized_row.get("desc")
                )
                if description:
                    product["description"] = str(description).strip()

                # Clean nulls
                product = _clean_dict(product)
                products.append(product)

    except Exception as e:
        errors.append(str(e))

    return {
        "products": products,
        "rows_processed": rows_processed,
        "rows_parsed": len(products),
        "errors": errors,
        "source_type": "csv",
        "parser": "csv_products",
    }


def _to_float(val) -> float | None:
    """Convert to float or None."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _clean_dict(d: dict) -> dict:
    """Remove keys with None or empty string values."""
    if not isinstance(d, dict):
        return d
    return {
        k: _clean_dict(v) if isinstance(v, dict) else v
        for k, v in d.items()
        if v is not None and v != "" and (not isinstance(v, dict) or any(_clean_dict(v).values()))
    }
