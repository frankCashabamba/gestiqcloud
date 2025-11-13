"""XML parser for products."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any


def parse_xml_products(file_path: str) -> dict[str, Any]:
    """Parse XML file with product data.

    Supports flexible XML structures with common product fields:
    - name/producto/producto_nombre
    - price/precio/unit_price/precio_unitario
    - quantity/cantidad/stock
    - sku/codigo/code
    - category/categoria
    - description/descripcion

    Args:
        file_path: Path to XML file

    Returns:
        Dict with 'products' list and metadata
    """
    products = []
    errors = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Remove namespace for easier parsing
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Find product elements (common names: producto, product, item, article)
        product_elements = []
        for tag in ["product", "producto", "item", "article", "articulo", "row", "fila"]:
            product_elements.extend(root.findall(f".//{tag}"))

        # If no explicit product elements, assume root has children that are products
        if not product_elements:
            product_elements = list(root)

        for idx, prod_elem in enumerate(product_elements, start=1):
            try:
                product = _parse_product_element(prod_elem, idx)
                if product:
                    products.append(product)
            except Exception as e:
                errors.append(f"Error parsing product {idx}: {str(e)}")

    except ET.ParseError as e:
        errors.append(f"XML parsing error: {str(e)}")
    except Exception as e:
        errors.append(f"Error reading XML: {str(e)}")

    return {
        "products": products,
        "rows_processed": len(product_elements) if product_elements else 0,
        "rows_parsed": len(products),
        "errors": errors,
        "source_type": "xml",
        "parser": "xml_products",
    }


def _parse_product_element(elem: ET.Element, idx: int) -> dict[str, Any] | None:
    """Extract product data from XML element.

    Args:
        elem: XML element
        idx: Element index

    Returns:
        Dict with product data or None
    """
    # Extract name/title
    name = None
    for tag in ["name", "nombre", "product_name", "producto_nombre", "title", "titulo"]:
        name_elem = elem.find(tag)
        if name_elem is not None and name_elem.text:
            name = str(name_elem.text).strip()
            break

    # Try attributes if no child element found
    if not name:
        name = elem.get("name") or elem.get("nombre") or elem.get("producto")

    # If still no name, skip
    if not name:
        return None

    # Extract price
    price = None
    for tag in ["price", "precio", "unit_price", "precio_unitario", "cost", "costo"]:
        price_elem = elem.find(tag)
        if price_elem is not None:
            price = _to_float(price_elem.text)
            if price is not None:
                break

    if price is None:
        price = _to_float(elem.get("price") or elem.get("precio"))

    # Extract quantity/stock
    quantity = None
    for tag in ["quantity", "cantidad", "stock", "existencia", "qty"]:
        qty_elem = elem.find(tag)
        if qty_elem is not None:
            quantity = _to_float(qty_elem.text)
            if quantity is not None:
                break

    if quantity is None:
        quantity = _to_float(elem.get("quantity") or elem.get("cantidad"))

    # Extract SKU
    sku = None
    for tag in ["sku", "codigo", "code", "reference", "referencia"]:
        sku_elem = elem.find(tag)
        if sku_elem is not None and sku_elem.text:
            sku = str(sku_elem.text).strip()
            break

    if not sku:
        sku = elem.get("sku") or elem.get("codigo")

    # Extract category
    category = None
    for tag in ["category", "categoria", "category_name", "category_id"]:
        cat_elem = elem.find(tag)
        if cat_elem is not None and cat_elem.text:
            category = str(cat_elem.text).strip()
            break

    if not category:
        category = elem.get("category") or elem.get("categoria") or "GENERAL"

    # Extract description
    description = None
    for tag in ["description", "descripcion", "desc", "remarks", "observaciones"]:
        desc_elem = elem.find(tag)
        if desc_elem is not None and desc_elem.text:
            description = str(desc_elem.text).strip()
            break

    if not description:
        description = elem.get("description") or elem.get("descripcion")

    # Build product dict
    product = {
        "doc_type": "product",
        "nombre": str(name).strip(),
        "name": str(name).strip(),
        "producto": str(name).strip(),
        "price": price or 0.0,
        "precio": price or 0.0,
        "quantity": quantity or 0.0,
        "cantidad": quantity or 0.0,
        "stock": quantity or 0.0,
        "category": str(category).strip() if category else "GENERAL",
        "categoria": str(category).strip() if category else "GENERAL",
        "source": "xml",
        "_metadata": {
            "parser": "xml_products",
            "element_index": idx,
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }

    if sku:
        product["sku"] = str(sku).strip()

    if description:
        product["description"] = str(description).strip()

    return product


def _to_float(val: str | None) -> float | None:
    """Convert string to float."""
    if not val:
        return None
    try:
        return float(str(val).replace(",", ".").strip())
    except (ValueError, TypeError):
        return None
