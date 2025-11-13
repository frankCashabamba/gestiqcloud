"""
Tests para task_promote - Promoción de documentos canónicos a tablas destino.

Cubre:
  - Promoción individual de items
  - Promoción de batches
  - Validación antes de promoción
  - Handlers para invoice, expense, bank_tx, product
"""

import pytest

from app.modules.imports.domain.canonical_schema import CanonicalDocument, validate_canonical
from app.modules.imports.domain.handlers_router import HandlersRouter


class TestPromotionValidation:
    """Tests para validación antes de promoción."""

    def test_canonical_invoice_valid_for_promotion(self):
        """Factura canónica debe pasar validación."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "invoice_number": "001-002-000123",
            "vendor": {"name": "Proveedor SA", "tax_id": "1792012345001"},
            "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0},
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Document should be valid. Errors: {errors}"

    def test_canonical_product_valid_for_promotion(self):
        """Producto canónico debe pasar validación."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "country": "EC",
            "currency": "USD",
            "product": {
                "name": "Laptop Dell",
                "sku": "LAP-001",
                "price": 1200.0,
                "stock": 5,
                "category": "Electrónica",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Product should be valid. Errors: {errors}"

    def test_canonical_expense_valid_for_promotion(self):
        """Gasto canónico debe pasar validación."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "country": "EC",
            "currency": "USD",
            "expense": {
                "description": "Combustible",
                "amount": 50.0,
                "expense_date": "2025-01-15",
                "category": "combustible",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Expense should be valid. Errors: {errors}"

    def test_canonical_bank_tx_valid_for_promotion(self):
        """Transacción bancaria canónica debe pasar validación."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia recibida",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Bank transaction should be valid. Errors: {errors}"


class TestHandlersRouter:
    """Tests para HandlersRouter."""

    def test_router_has_handler_for_invoice(self):
        """Router debe tener handler para invoice."""
        handler = HandlersRouter.get_handler_for_type("invoice")
        assert handler is not None
        assert handler.__name__ == "InvoiceHandler"

    def test_router_has_handler_for_product(self):
        """Router debe tener handler para product."""
        handler = HandlersRouter.get_handler_for_type("product")
        assert handler is not None
        assert handler.__name__ == "ProductHandler"

    def test_router_has_handler_for_expense(self):
        """Router debe tener handler para expense."""
        handler = HandlersRouter.get_handler_for_type("expense")
        assert handler is not None
        assert handler.__name__ == "ExpenseHandler"

    def test_router_has_handler_for_bank_tx(self):
        """Router debe tener handler para bank_tx."""
        handler = HandlersRouter.get_handler_for_type("bank_tx")
        assert handler is not None
        assert handler.__name__ == "BankHandler"

    def test_router_gets_target_for_invoice(self):
        """Router debe retornar 'invoices' como target para invoice."""
        target = HandlersRouter.get_target_for_type("invoice")
        assert target == "invoices"

    def test_router_gets_target_for_product(self):
        """Router debe retornar 'inventory' como target para product."""
        target = HandlersRouter.get_target_for_type("product")
        assert target == "inventory"

    def test_router_gets_target_for_expense(self):
        """Router debe retornar 'expenses' como target para expense."""
        target = HandlersRouter.get_target_for_type("expense")
        assert target == "expenses"

    def test_router_gets_target_for_bank_tx(self):
        """Router debe retornar 'bank_movements' como target para bank_tx."""
        target = HandlersRouter.get_target_for_type("bank_tx")
        assert target == "bank_movements"

    def test_router_handles_aliases(self):
        """Router debe manejar aliases de doc_type."""
        # Alias "factura" para invoice
        handler = HandlersRouter.get_handler_for_type("factura")
        assert handler is not None
        assert handler.__name__ == "InvoiceHandler"

        target = HandlersRouter.get_target_for_type("factura")
        assert target == "invoices"

        # Alias "gasto" para expense
        handler = HandlersRouter.get_handler_for_type("gasto")
        assert handler is not None
        assert handler.__name__ == "ExpenseHandler"

        target = HandlersRouter.get_target_for_type("gasto")
        assert target == "expenses"


class TestCanonicalToNormalized:
    """Tests para conversión canonical → normalized."""

    def test_convert_invoice_canonical_to_normalized(self):
        """Conversión de invoice canónico a formato normalized."""
        from app.modules.imports.domain.handlers_router import _canonical_to_normalized

        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "invoice_number": "INV-001",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Proveedor SA", "tax_id": "1792012345001"},
            "buyer": {"name": "Mi Empresa"},
            "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0},
        }
        normalized = _canonical_to_normalized(doc)

        assert normalized["vendor_name"] == "Proveedor SA"
        assert normalized["buyer_name"] == "Mi Empresa"
        assert normalized["subtotal"] == 100.0
        assert normalized["tax"] == 12.0
        assert normalized["total"] == 112.0

    def test_convert_product_canonical_to_normalized(self):
        """Conversión de product canónico a formato normalized."""
        from app.modules.imports.domain.handlers_router import _canonical_to_normalized

        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {
                "name": "Laptop",
                "sku": "LAP-001",
                "price": 1200.0,
                "stock": 5,
                "category": "Electrónica",
            },
        }
        normalized = _canonical_to_normalized(doc)

        assert normalized["name"] == "Laptop"
        assert normalized["sku"] == "LAP-001"
        assert normalized["price"] == 1200.0
        assert normalized["stock"] == 5
        assert normalized["category"] == "Electrónica"

    def test_convert_expense_canonical_to_normalized(self):
        """Conversión de expense canónico a formato normalized."""
        from app.modules.imports.domain.handlers_router import _canonical_to_normalized

        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Combustible",
                "amount": 50.0,
                "expense_date": "2025-01-15",
                "category": "combustible",
                "payment_method": "card",
            },
        }
        normalized = _canonical_to_normalized(doc)

        assert normalized["description"] == "Combustible"
        assert normalized["amount"] == 50.0
        assert normalized["expense_date"] == "2025-01-15"
        assert normalized["category"] == "combustible"
        assert normalized["payment_method"] == "card"

    def test_convert_bank_tx_canonical_to_normalized(self):
        """Conversión de bank_tx canónico a formato normalized."""
        from app.modules.imports.domain.handlers_router import _canonical_to_normalized

        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia",
                "counterparty": "Cliente ABC",
            },
        }
        normalized = _canonical_to_normalized(doc)

        assert normalized["amount"] == 1500.0
        assert normalized["direction"] == "credit"
        assert normalized["narrative"] == "Transferencia"
        assert normalized["counterparty_name"] == "Cliente ABC"


class TestPromotionFlow:
    """Tests end-to-end del flujo de promoción."""

    def test_promotion_flow_invoice_to_invoices(self):
        """Flujo: invoice canónico → target=invoices."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "invoice_number": "INV-001",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Proveedor SA"},
            "totals": {"subtotal": 100.0, "tax": 12.0, "total": 112.0},
        }

        # Validar
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Document should be valid. Errors: {errors}"

        # Router debe reconocer el tipo
        handler = HandlersRouter.get_handler_for_type(doc.get("doc_type"))
        assert handler is not None

        target = HandlersRouter.get_target_for_type(doc.get("doc_type"))
        assert target == "invoices"

    def test_promotion_flow_product_to_inventory(self):
        """Flujo: product canónico → target=inventory."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {
                "name": "Producto A",
                "price": 100.0,
                "stock": 10,
            },
        }

        # Validar
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Document should be valid. Errors: {errors}"

        # Router debe reconocer el tipo
        handler = HandlersRouter.get_handler_for_type(doc.get("doc_type"))
        assert handler is not None

        target = HandlersRouter.get_target_for_type(doc.get("doc_type"))
        assert target == "inventory"

    def test_promotion_flow_expense_to_expenses(self):
        """Flujo: expense canónico → target=expenses."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Gasto",
                "amount": 50.0,
                "expense_date": "2025-01-15",
            },
        }

        # Validar
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Document should be valid. Errors: {errors}"

        # Router debe reconocer el tipo
        handler = HandlersRouter.get_handler_for_type(doc.get("doc_type"))
        assert handler is not None

        target = HandlersRouter.get_target_for_type(doc.get("doc_type"))
        assert target == "expenses"

    def test_promotion_flow_bank_tx_to_bank_movements(self):
        """Flujo: bank_tx canónico → target=bank_movements."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {
                "amount": 1000.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia",
            },
        }

        # Validar
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Document should be valid. Errors: {errors}"

        # Router debe reconocer el tipo
        handler = HandlersRouter.get_handler_for_type(doc.get("doc_type"))
        assert handler is not None

        target = HandlersRouter.get_target_for_type(doc.get("doc_type"))
        assert target == "bank_movements"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
