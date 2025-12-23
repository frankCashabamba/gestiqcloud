"""Parsers registry for import module."""

from collections.abc import Callable
from enum import Enum
from typing import Any


class DocType(Enum):
    PRODUCTS = "products"
    BANK_TRANSACTIONS = "bank_transactions"
    INVOICES = "invoices"
    EXPENSES = "expenses"
    RECIPES = "recipes"
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

    def get_parser(self, parser_id: str) -> dict[str, Any] | None:
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


def _register_parsers():
    """Register all available parsers."""
    from .csv_bank import parse_csv_bank
    from .csv_invoices import parse_csv_invoices
    from .csv_products import parse_csv_products
    from .generic_excel import parse_excel_generic
    from .pdf_qr import parse_pdf_qr
    from .products_excel import parse_products_excel
    from .xlsx_bank import parse_xlsx_bank
    from .xlsx_expenses import parse_xlsx_expenses
    from .xlsx_invoices import parse_xlsx_invoices
    from .xml_camt053_bank import parse_xml_camt053_bank
    from .xml_invoice import parse_xml_invoice
    from .xlsx_recipes import parse_xlsx_recipes
    from .pdf_ocr import parse_pdf_ocr
    from .xml_facturae import parse_facturae
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
        "xlsx_bank",
        DocType.BANK_TRANSACTIONS,
        parse_xlsx_bank,
        "Excel/XLS parser for bank transactions",
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
        "xlsx_invoices",
        DocType.INVOICES,
        parse_xlsx_invoices,
        "Excel parser for invoices data",
    )
    registry.register(
        "pdf_qr",
        DocType.INVOICES,
        parse_pdf_qr,
        "PDF parser with QR code extraction for invoices and receipts",
    )
    registry.register(
        "xlsx_recipes",
        DocType.RECIPES,
        parse_xlsx_recipes,
        "Excel parser for recipe costing sheets with ingredients and pricing",
    )
    registry.register(
        "xml_facturae",
        DocType.INVOICES,
        parse_facturae,
        "Spanish Facturae XML parser for electronic invoices (gob.es format)",
    )
    registry.register(
        "pdf_ocr",
        DocType.GENERIC,
        parse_pdf_ocr,
        "PDF parser with OCR for tickets, receipts, invoices and general documents",
    )


_register_parsers()
