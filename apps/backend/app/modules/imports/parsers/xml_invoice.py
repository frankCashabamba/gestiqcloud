"""
Parser para facturas en formato XML (estándar UBL/CFDI).

Soporta:
- Facturas electrónicas ecuatorianas (XML de SRI)
- CFDI (México)
- UBL estándar

Salida: CanonicalDocument con doc_type='invoice'
"""

import xml.etree.ElementTree as ET
from typing import Any


def parse_xml_invoice(file_path: str) -> dict[str, Any]:
    """
    Parse XML invoice file.

    Args:
        file_path: Path to XML file

    Returns:
        Dict with 'invoices' list and metadata
    """
    invoices = []
    errors = []

    try:
        tree = ET.parse(file_path)
        root = tree.getroot()

        # Detectar namespace
        namespaces = _detect_namespaces(root)

        # Extraer factura según tipo
        invoice = _extract_invoice_data(root, namespaces)
        if invoice:
            invoice["source"] = "xml"
            invoice["confidence"] = 0.9
            invoice["_metadata"] = {"parser": "xml_invoice"}
            invoices.append(invoice)
        else:
            errors.append("No se pudo extraer datos de factura del XML")

    except ET.ParseError as e:
        errors.append(f"Error parsing XML: {str(e)}")
    except Exception as e:
        errors.append(f"Unexpected error: {str(e)}")

    return {
        "invoices": invoices,
        "errors": errors,
        "rows_processed": 1,
        "rows_parsed": len(invoices),
        "source_type": "xml",
        "parser": "xml_invoice",
    }


def _detect_namespaces(root: ET.Element) -> dict[str, str]:
    """Detectar namespaces del elemento raíz."""
    ns = {}
    if root.tag.startswith("{"):
        # UBL
        ns["ubl"] = root.tag.split("}")[0][1:]

    # CFDI
    for attr_name, attr_value in root.attrib.items():
        if "cfdi" in attr_name.lower():
            ns["cfdi"] = attr_value

    return ns


def _extract_invoice_data(root: ET.Element, namespaces: dict) -> dict[str, Any] | None:
    """Extraer datos de factura según el namespace."""

    # Intenta primero UBL (Ecuador/España/etc)
    if "ubl" in namespaces:
        return _extract_ubl_invoice(root, namespaces["ubl"])

    # Intenta CFDI (México)
    for attr_value in namespaces.values():
        if "cfdi" in attr_value:
            return _extract_cfdi_invoice(root, attr_value)

    # Fallback: generic XML parsing
    return _extract_generic_invoice(root)


def _extract_ubl_invoice(root: ET.Element, ns: str) -> dict[str, Any] | None:
    """Extraer datos de factura UBL."""

    def tag(name: str) -> str:
        return f"{{{ns}}}{name}"

    try:
        # Datos básicos
        invoice_number = _get_text(root, f".//{tag('ID')}")
        issue_date = _get_text(root, f".//{tag('IssueDate')}")
        due_date = _get_text(root, f".//{tag('DueDate')}")

        # Vendor/Supplier (AccountingSupplierParty)
        supplier_elem = root.find(f".//{tag('AccountingSupplierParty')}")
        vendor = {}
        if supplier_elem is not None:
            vendor_party = supplier_elem.find(f".//{tag('Party')}")
            if vendor_party is not None:
                vendor = {
                    "name": _get_text(vendor_party, f".//{tag('Name')}"),
                    "tax_id": _get_text(vendor_party, f".//{tag('CompanyID')}"),
                }

        # Buyer/Customer (AccountingCustomerParty)
        customer_elem = root.find(f".//{tag('AccountingCustomerParty')}")
        buyer = {}
        if customer_elem is not None:
            buyer_party = customer_elem.find(f".//{tag('Party')}")
            if buyer_party is not None:
                buyer = {
                    "name": _get_text(buyer_party, f".//{tag('Name')}"),
                    "tax_id": _get_text(buyer_party, f".//{tag('CompanyID')}"),
                }

        # Totals
        legal_total = root.find(f".//{tag('LegalMonetaryTotal')}")
        totals = {}
        if legal_total is not None:
            totals = {
                "subtotal": _to_float(_get_text(legal_total, f".//{tag('LineExtensionAmount')}")),
                "tax": _to_float(
                    _get_text(legal_total, f".//{tag('TaxTotal')}/{tag('TaxAmount')}")
                ),
                "total": _to_float(_get_text(legal_total, f".//{tag('PayableAmount')}")),
            }

        # Currency
        currency = _get_text(root, f".//{tag('DocumentCurrencyCode')}") or "USD"

        # Lines
        lines = []
        for line_elem in root.findall(f".//{tag('InvoiceLine')}"):
            line = {
                "desc": _get_text(line_elem, f".//{tag('Item')}/{tag('Description')}"),
                "qty": _to_float(_get_text(line_elem, f".//{tag('InvoicedQuantity')}")),
                "unit_price": _to_float(
                    _get_text(line_elem, f".//{tag('Price')}/{tag('PriceAmount')}")
                ),
                "total": _to_float(_get_text(line_elem, f".//{tag('LineExtensionAmount')}")),
            }
            lines.append({k: v for k, v in line.items() if v is not None})

        return {
            "doc_type": "invoice",
            "invoice_number": invoice_number,
            "issue_date": issue_date,
            "due_date": due_date,
            "vendor": vendor,
            "buyer": buyer,
            "totals": totals,
            "currency": currency,
            "lines": lines,
            "country": "EC",  # Default Ecuador
        }

    except Exception:
        return None


def _extract_cfdi_invoice(root: ET.Element, ns: str) -> dict[str, Any] | None:
    """Extract CFDI invoice data (Mexico)."""
    try:
        # Implementar parsing de CFDI aquí
        # Por ahora, retorna estructura básica
        return {
            "doc_type": "invoice",
            "invoice_number": root.attrib.get("Folio", ""),
            "issue_date": root.attrib.get("Fecha", ""),
            "currency": root.attrib.get("Moneda", "MXN"),
            "country": "MX",
            "source": "xml",
        }
    except Exception:
        return None


def _extract_generic_invoice(root: ET.Element) -> dict[str, Any] | None:
    """Fallback: extract generic data."""
    try:
        return {
            "doc_type": "invoice",
            "invoice_number": root.findtext("invoice_number") or root.findtext("number"),
            "issue_date": root.findtext("issue_date") or root.findtext("date"),
            "vendor": {
                "name": root.findtext("vendor_name") or root.findtext("vendor"),
            },
            "country": "EC",
        }
    except Exception:
        return None


def _get_text(elem: ET.Element, xpath: str) -> str | None:
    """Obtener texto de un elemento."""
    try:
        found = elem.findtext(xpath)
        return found if found else None
    except Exception:
        return None


def _to_float(val) -> float | None:
    """Convertir a float."""
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", "."))
    except (ValueError, TypeError):
        return None
