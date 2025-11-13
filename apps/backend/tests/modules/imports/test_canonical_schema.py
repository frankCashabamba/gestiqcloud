"""
Tests para schema canónico SPEC-1.

Cubre validación, conversión legacy y construcción de documentos.
"""

import pytest
from app.modules.imports.domain.canonical_schema import (
    CanonicalDocument,
    validate_canonical,
    build_routing_proposal,
    validate_totals,
    validate_tax_breakdown,
)
from app.modules.imports.parsers import registry
from app.modules.imports.services.classifier import classifier


class TestCanonicalValidation:
    """Tests de validación de schema canónico."""

    def test_valid_invoice_minimal(self):
        """Factura mínima válida."""
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
        assert is_valid
        assert len(errors) == 0

    def test_invalid_doc_type_missing(self):
        """doc_type es obligatorio."""
        doc = {
            "country": "EC",
            "currency": "USD",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("doc_type" in err for err in errors)

    def test_invalid_country(self):
        """País no soportado."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "XX",  # No existe
            "currency": "USD",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("country" in err for err in errors)

    def test_invalid_currency(self):
        """Moneda no soportada."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "XXX",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("currency" in err for err in errors)

    def test_invalid_date_format(self):
        """Fecha en formato incorrecto."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "issue_date": "15/01/2025",  # Debe ser YYYY-MM-DD
            "invoice_number": "001",
            "vendor": {"name": "Test"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("issue_date" in err for err in errors)

    def test_invoice_requires_invoice_number(self):
        """Facturas requieren número."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "issue_date": "2025-01-15",
            "vendor": {"name": "Test"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("invoice_number" in err for err in errors)

    def test_expense_receipt_requires_date_and_total(self):
        """Recibos requieren fecha y total."""
        doc: CanonicalDocument = {
            "doc_type": "expense_receipt",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("issue_date" in err for err in errors)
        assert any("totals.total" in err for err in errors)

    def test_bank_tx_requires_bank_tx_block(self):
        """Transacciones bancarias requieren bloque bank_tx."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("bank_tx" in err for err in errors)

    def test_bank_tx_validates_direction(self):
        """Dirección debe ser debit o credit."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {
                "amount": 100.0,
                "direction": "invalid",
                "value_date": "2025-01-15",
                "narrative": "Test",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("direction" in err for err in errors)


class TestTotalsValidation:
    """Tests de validación de totales."""

    def test_totals_valid(self):
        """Totales correctos."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 112.0}
        errors = validate_totals(totals)  # noqa: F841
        assert len(errors) == 0

    def test_totals_mismatch(self):
        """Totales no cuadran."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 120.0}
        errors = validate_totals(totals)  # noqa: F841
        assert len(errors) > 0
        assert "no cuadra" in errors[0]

    def test_totals_with_rounding_tolerance(self):
        """Tolera diferencias de redondeo."""
        totals = {"subtotal": 100.0, "tax": 12.0, "total": 112.005}
        errors = validate_totals(totals)  # noqa: F841
        assert len(errors) == 0


class TestTaxBreakdownValidation:
    """Tests de validación de desglose fiscal."""

    def test_tax_breakdown_valid(self):
        """Desglose válido."""
        breakdown = [
            {"code": "IVA12-EC", "rate": 12.0, "amount": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)  # noqa: F841
        assert len(errors) == 0

    def test_tax_breakdown_missing_code(self):
        """Falta código."""
        breakdown = [
            {"rate": 12.0, "amount": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)  # noqa: F841
        assert len(errors) > 0
        assert "code" in errors[0]["field"]

    def test_tax_breakdown_missing_amount(self):
        """Falta monto."""
        breakdown = [
            {"code": "IVA12", "rate": 12.0},
        ]
        errors = validate_tax_breakdown(breakdown)  # noqa: F841
        assert len(errors) > 0
        assert "amount" in errors[0]["field"]


class TestRoutingProposal:
    """Tests de propuestas de enrutamiento."""

    def test_build_routing_proposal_invoice(self):
        """Propuesta para factura."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "totals": {"total": 100.0},
        }
        proposal = build_routing_proposal(doc, "FUEL", "6230", 0.85)

        assert proposal["target"] == "expenses"
        assert proposal["category_code"] == "FUEL"
        assert proposal["account"] == "6230"
        assert proposal["confidence"] == 0.85

    def test_build_routing_proposal_bank_tx(self):
        """Propuesta para transacción bancaria."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "bank_tx": {"amount": 1000.0, "direction": "credit"},
        }
        proposal = build_routing_proposal(doc, confidence=0.7)

        assert proposal["target"] == "bank_movements"
        assert proposal["confidence"] == 0.7


class TestProductValidation:
    """Tests de validación para productos (Fase C)."""

    def test_valid_product_minimal(self):
        """Producto mínimo válido."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {
                "name": "Laptop Dell",
                "price": 1200.00,
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"
        assert len(errors) == 0

    def test_valid_product_complete(self):
        """Producto completo con todos los campos."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "country": "EC",
            "currency": "USD",
            "product": {
                "name": "Laptop Dell XPS 13",
                "sku": "LAP-0001",
                "price": 1200.00,
                "stock": 5,
                "category": "Electrónica",
                "unit": "pcs",
                "description": "Laptop de alto rendimiento",
                "barcode": "123456789",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_product_requires_name(self):
        """Producto requiere nombre."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {"price": 100.0},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("name" in err for err in errors)

    def test_product_requires_price(self):
        """Producto requiere precio."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {"name": "Test"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("price" in err for err in errors)

    def test_product_price_must_be_positive(self):
        """Precio no puede ser negativo."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {"name": "Test", "price": -100.0},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("price" in err and ">= 0" in err for err in errors)

    def test_product_stock_must_be_positive(self):
        """Stock no puede ser negativo."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {"name": "Test", "price": 100.0, "stock": -5},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("stock" in err for err in errors)

    def test_product_routing_proposal(self):
        """Propuesta de enrutamiento para producto."""
        doc: CanonicalDocument = {
            "doc_type": "product",
            "product": {"name": "Test", "price": 100.0},
        }
        proposal = build_routing_proposal(doc)
        assert proposal["target"] == "inventory"


class TestExpenseValidation:
    """Tests de validación para gastos (Fase C)."""

    def test_valid_expense_minimal(self):
        """Gasto mínimo válido."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Combustible",
                "amount": 50.00,
                "expense_date": "2025-01-15",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"
        assert len(errors) == 0

    def test_valid_expense_complete(self):
        """Gasto completo con todos los campos."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "country": "EC",
            "currency": "USD",
            "expense": {
                "description": "Combustible gasolina",
                "amount": 50.00,
                "expense_date": "2025-01-15",
                "category": "combustible",
                "subcategory": "gasolina",
                "payment_method": "card",
                "vendor": {"name": "Estación YPF"},
                "receipt_number": "RCP-12345",
                "notes": "Llenado del tanque principal",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_expense_requires_description(self):
        """Gasto requiere descripción."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {"amount": 50.00, "expense_date": "2025-01-15"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("description" in err for err in errors)

    def test_expense_requires_amount(self):
        """Gasto requiere monto."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {"description": "Test", "expense_date": "2025-01-15"},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("amount" in err for err in errors)

    def test_expense_requires_date(self):
        """Gasto requiere fecha."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {"description": "Test", "amount": 50.0},
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("expense_date" in err for err in errors)

    def test_expense_amount_must_be_positive(self):
        """Monto debe ser > 0."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Test",
                "amount": 0,
                "expense_date": "2025-01-15",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("amount" in err and "> 0" in err for err in errors)

    def test_expense_date_format(self):
        """Fecha debe ser YYYY-MM-DD."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Test",
                "amount": 50.0,
                "expense_date": "15/01/2025",  # Formato incorrecto
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("expense_date" in err for err in errors)

    def test_expense_payment_method_validation(self):
        """Método de pago debe ser válido."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Test",
                "amount": 50.0,
                "expense_date": "2025-01-15",
                "payment_method": "invalid_method",
            },
        }
        is_valid, errors = validate_canonical(doc)
        assert not is_valid
        assert any("payment_method" in err for err in errors)

    def test_expense_routing_proposal(self):
        """Propuesta de enrutamiento para gasto."""
        doc: CanonicalDocument = {
            "doc_type": "expense",
            "expense": {
                "description": "Test",
                "amount": 50.0,
                "expense_date": "2025-01-15",
            },
        }
        proposal = build_routing_proposal(doc)
        assert proposal["target"] == "expenses"


class TestCompleteExamples:
    """Tests con ejemplos completos."""

    def test_complete_invoice_ecuador(self):
        """Factura completa de Ecuador."""
        doc: CanonicalDocument = {
            "doc_type": "invoice",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "due_date": "2025-02-15",
            "invoice_number": "001-002-000123",
            "vendor": {
                "name": "Proveedor SA",
                "tax_id": "1792012345001",
                "country": "EC",
                "address": "Quito, Ecuador",
            },
            "buyer": {
                "name": "Mi Empresa SRL",
                "tax_id": "1791234567001",
            },
            "totals": {
                "subtotal": 100.0,
                "tax": 12.0,
                "total": 112.0,
                "tax_breakdown": [
                    {"code": "IVA12-EC", "rate": 12.0, "amount": 12.0, "base": 100.0}
                ],
            },
            "lines": [
                {
                    "desc": "Suministros de oficina",
                    "qty": 10.0,
                    "unit": "pcs",
                    "unit_price": 10.0,
                    "total": 100.0,
                    "tax_code": "IVA12",
                    "tax_amount": 12.0,
                }
            ],
            "payment": {"method": "transfer", "iban": "EC12345678901234567890"},
            "routing_proposal": {
                "target": "expenses",
                "category_code": "SUPPLIES",
                "account": "6290",
                "confidence": 0.85,
            },
            "source": "xml",
            "confidence": 0.95,
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"

    def test_complete_bank_transaction(self):
        """Transacción bancaria completa."""
        doc: CanonicalDocument = {
            "doc_type": "bank_tx",
            "country": "EC",
            "currency": "USD",
            "issue_date": "2025-01-15",
            "bank_tx": {
                "amount": 1500.0,
                "direction": "credit",
                "value_date": "2025-01-15",
                "narrative": "Transferencia cliente ABC",
                "counterparty": "Cliente ABC SA",
                "external_ref": "TRX20250115001",
            },
            "routing_proposal": {
                "target": "bank_movements",
                "confidence": 0.90,
            },
            "source": "camt053",
            "confidence": 0.95,
        }

        is_valid, errors = validate_canonical(doc)
        assert is_valid, f"Errores: {errors}"


class TestParserRegistry:
    """Tests para el registry de parsers."""

    def test_registry_has_registered_parsers(self):
        """Registry tiene parsers registrados."""
        parsers = registry.list_parsers()
        assert len(parsers) >= 2
        assert "generic_excel" in parsers
        assert "products_excel" in parsers

    def test_get_parser_info(self):
        """Obtener información de parser."""
        parser = registry.get_parser("products_excel")
        assert parser is not None
        assert parser["doc_type"] == "products"
        assert callable(parser["handler"])

    def test_get_parsers_for_type(self):
        """Obtener parsers por tipo de documento."""
        products_parsers = registry.get_parsers_for_type(registry.DocType.PRODUCTS)
        assert "products_excel" in products_parsers

    def test_get_nonexistent_parser(self):
        """Parser inexistente retorna None."""
        parser = registry.get_parser("nonexistent")
        assert parser is None


class TestFileClassifier:
    """Tests para el clasificador de archivos."""

    def test_classifier_initialization(self):
        """Clasificador se inicializa correctamente."""
        assert classifier.parsers_info is not None
        assert len(classifier.parsers_info) >= 2

    def test_classify_unsupported_file(self):
        """Archivos no soportados son rechazados."""
        result = classifier.classify_file("/fake/path/test.txt", "test.txt")
        assert result["suggested_parser"] is None
        assert result["confidence"] == 0.0
        assert "Unsupported file type" in result["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
