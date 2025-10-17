import pytest
from app.modules.imports.validators import validate_invoices


class TestValidatorsIntegration:
    """Tests de integración con validators.py."""

    def test_validate_invoices_with_country_ec(self):
        invoice = {
            "invoice_number": "001-001-000000123",
            "invoice_date": "2025-01-15",
            "issuer_tax_id": "1713175071001",
            "net_amount": 100.0,
            "tax_amount": 12.0,
            "total_amount": 112.0,
            "tax_rate": 12.0,
            "currency": "USD",
        }
        
        errors = validate_invoices(invoice, country="EC")
        assert len(errors) == 0

    def test_validate_invoices_with_country_es(self):
        invoice = {
            "invoice_number": "FAC-2025-001",
            "invoice_date": "2025-01-15",
            "issuer_tax_id": "12345678Z",
            "net_amount": 100.0,
            "tax_amount": 21.0,
            "total_amount": 121.0,
            "tax_rate": 21.0,
            "currency": "EUR",
        }
        
        errors = validate_invoices(invoice, country="ES")
        assert len(errors) == 0

    def test_validate_invoices_invalid_ruc_ec(self):
        invoice = {
            "invoice_number": "001-001-000000123",
            "invoice_date": "2025-01-15",
            "issuer_tax_id": "1713175071009",
            "net_amount": 100.0,
            "tax_amount": 12.0,
            "total_amount": 112.0,
        }
        
        errors = validate_invoices(invoice, country="EC")
        assert any("dígito verificador" in e["msg"].lower() for e in errors)

    def test_validate_invoices_invalid_tax_rate_es(self):
        invoice = {
            "invoice_number": "FAC-2025-001",
            "invoice_date": "2025-01-15",
            "issuer_tax_id": "12345678Z",
            "net_amount": 100.0,
            "tax_amount": 12.0,
            "total_amount": 112.0,
            "tax_rate": 12.0,
        }
        
        errors = validate_invoices(invoice, country="ES")
        assert any("tasa de impuesto" in e["msg"].lower() for e in errors)

    def test_validate_invoices_without_country(self):
        """Sin país especificado, sólo validaciones genéricas."""
        invoice = {
            "invoice_number": "ANY-FORMAT",
            "invoice_date": "2025-01-15",
            "issuer_tax_id": "INVALID-TAX-ID",
            "net_amount": 100.0,
            "tax_amount": 12.0,
            "total_amount": 112.0,
        }
        
        errors = validate_invoices(invoice)
        assert len(errors) == 0
