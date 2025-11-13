"""Parsers registry for import module."""

from collections.abc import Callable
from enum import Enum
from typing import Any, Dict


class DocType(Enum):
    PRODUCTS = "products"
    BANK_TRANSACTIONS = "bank_transactions"
    INVOICES = "invoices"
    EXPENSES = "expenses"
    GENERIC = "generic"


class ParserRegistry:
    """Registry of available parsers."""

    def __init__(self):
        self._parsers: dict[str, dict[str, Any]] = {}

    def register(self, parser_id: str, doc_type: DocType, handler: Callable, description: str = ""):
        """Register a parser."""
        self._parsers[parser_id] = {
            "id": parser_id,
            "doc_type": doc_type.value,
            "handler": handler,
            "description": description,
        }

    def get_parser(self, parser_id: str) -> dict[str, Any]:
        """Get parser info by ID."""
        return self._parsers.get(parser_id)

    def list_parsers(self) -> dict[str, dict[str, Any]]:
        """List all registered parsers."""
        return self._parsers.copy()

    def get_parsers_for_type(self, doc_type: DocType) -> dict[str, dict[str, Any]]:
        """Get parsers for a specific document type."""
        return {k: v for k, v in self._parsers.items() if v["doc_type"] == doc_type.value}


# Global registry instance
registry = ParserRegistry()

# Register existing parsers
from .csv_bank import parse_csv_bank
from .csv_invoices import parse_csv_invoices
from .csv_products import parse_csv_products
from .generic_excel import parse_excel_generic
from .pdf_qr import parse_pdf_qr
from .products_excel import parse_products_excel
from .xlsx_expenses import parse_xlsx_expenses
from .xml_camt053_bank import parse_xml_camt053_bank
from .xml_invoice import parse_xml_invoice
from .xml_products import parse_xml_products

registry.register(
    "generic_excel",
    DocType.GENERIC,
    parse_excel_generic,
    "Generic Excel parser that auto-detects structure",
)

registry.register(
    "products_excel",
    DocType.PRODUCTS,
    parse_products_excel,
    "Specialized Excel parser for products with category detection",
)

registry.register(
    "csv_invoices", DocType.INVOICES, parse_csv_invoices, "CSV parser for invoice data"
)

registry.register(
    "csv_bank", DocType.BANK_TRANSACTIONS, parse_csv_bank, "CSV parser for bank transactions"
)

registry.register(
    "csv_products", DocType.PRODUCTS, parse_csv_products, "CSV parser for product data"
)

registry.register(
    "xml_invoice", DocType.INVOICES, parse_xml_invoice, "XML parser for UBL/CFDI invoices"
)

registry.register(
    "xml_camt053_bank",
    DocType.BANK_TRANSACTIONS,
    parse_xml_camt053_bank,
    "ISO 20022 CAMT.053 XML parser for bank statements",
)

registry.register(
    "xml_products", DocType.PRODUCTS, parse_xml_products, "XML parser for product data"
)

registry.register(
    "xlsx_expenses",
    DocType.EXPENSES,
    parse_xlsx_expenses,
    "Excel parser for expense and receipt data",
)

registry.register(
    "pdf_qr",
    DocType.INVOICES,
    parse_pdf_qr,
    "PDF parser with QR code extraction for invoices and receipts",
)
