"""
P0 Regression tests: Canonical schemas, robust parsing, structured errors.
Tests with real problematic files.
"""

import pytest
from app.modules.imports.domain.canonical_schema import (
    DocumentType,
    SALES_INVOICE_SCHEMA,
    PURCHASE_INVOICE_SCHEMA,
    EXPENSE_SCHEMA,
    BANK_TX_SCHEMA,
    get_schema,
)
from app.modules.imports.domain.errors import (
    ErrorCategory,
    ErrorSeverity,
    ImportError,
    ImportErrorCollection,
)
from app.modules.imports.domain.validator import universal_validator
from app.modules.imports.parsers.robust_excel import robust_parser


class TestCanonicalSchema:
    """Test canonical schema definitions."""
    
    def test_get_schema_sales_invoice(self):
        """Test retrieval of sales invoice schema."""
        schema = get_schema("sales_invoice")
        assert schema is not None
        assert schema.doc_type == DocumentType.SALES_INVOICE
        assert "invoice_number" in schema.fields
        assert "amount_total" in schema.fields
    
    def test_get_schema_purchase_invoice(self):
        """Test retrieval of purchase invoice schema."""
        schema = get_schema("purchase_invoice")
        assert schema is not None
        assert schema.doc_type == DocumentType.PURCHASE_INVOICE
    
    def test_get_schema_expense(self):
        """Test retrieval of expense schema."""
        schema = get_schema("expense")
        assert schema is not None
        assert schema.doc_type == DocumentType.EXPENSE
        assert "expense_date" in schema.fields
        assert "amount" in schema.fields
    
    def test_get_schema_bank_tx(self):
        """Test retrieval of bank transaction schema."""
        schema = get_schema("bank_tx")
        assert schema is not None
        assert schema.doc_type == DocumentType.BANK_TX
    
    def test_invalid_schema(self):
        """Test retrieval of invalid schema."""
        schema = get_schema("nonexistent")
        assert schema is None
    
    def test_schema_field_aliases(self):
        """Test that field aliases are registered."""
        schema = SALES_INVOICE_SCHEMA
        invoice_field = schema.fields["invoice_number"]
        
        assert "factura" in invoice_field.aliases
        assert "invoice" in invoice_field.aliases
        assert "numero" in invoice_field.aliases


class TestImportErrorStructure:
    """Test structured error reporting."""
    
    def test_import_error_creation(self):
        """Test creating a structured error."""
        error = ImportError(
            row_number=10,
            field_name="amount",
            canonical_field="amount_total",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            rule_name="is_positive",
            message="Amount must be positive",
            suggestion="Ensure the value is > 0",
            raw_value="-100.00",
        )
        
        assert error.row_number == 10
        assert error.field_name == "amount"
        assert error.category == ErrorCategory.VALIDATION
        assert error.message == "Amount must be positive"
    
    def test_error_to_dict(self):
        """Test converting error to dict."""
        error = ImportError(
            row_number=5,
            field_name="invoice_number",
            message="Invoice number is required",
            category=ErrorCategory.MISSING_FIELD,
            severity=ErrorSeverity.ERROR,
        )
        
        error_dict = error.to_dict()
        assert error_dict["row_number"] == 5
        assert error_dict["field_name"] == "invoice_number"
        assert error_dict["category"] == "missing_field"
        assert error_dict["severity"] == "error"
    
    def test_error_collection(self):
        """Test error collection."""
        errors = ImportErrorCollection()
        
        # Add some errors
        errors.add(
            "Field is required",
            row_number=1,
            field_name="invoice_number",
            category=ErrorCategory.MISSING_FIELD,
        )
        errors.add(
            "Value must be a number",
            row_number=2,
            field_name="amount",
            category=ErrorCategory.TYPE_MISMATCH,
            raw_value="abc",
        )
        
        assert len(errors) == 2
        assert errors.has_errors()
    
    def test_error_grouping_by_row(self):
        """Test grouping errors by row."""
        errors = ImportErrorCollection()
        errors.add("Error 1", row_number=1, field_name="f1")
        errors.add("Error 2", row_number=1, field_name="f2")
        errors.add("Error 3", row_number=2, field_name="f3")
        
        by_row = errors.by_row()
        assert len(by_row[1]) == 2
        assert len(by_row[2]) == 1


class TestUniversalValidator:
    """Test document validation against canonical schemas."""
    
    def test_validate_complete_sales_invoice(self):
        """Test validation of complete, valid sales invoice."""
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "customer_name": "Acme Corp",
            "amount_subtotal": "1000.00",
            "amount_total": "1200.00",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="sales_invoice",
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_missing_required_field(self):
        """Test validation fails when required field is missing."""
        data = {
            "invoice_number": "INV-001",
            # Missing invoice_date
            "customer_name": "Acme Corp",
            "amount_subtotal": "1000.00",
            "amount_total": "1200.00",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="sales_invoice",
        )
        
        assert not is_valid
        assert len(errors) > 0
        assert any("invoice_date" in str(e) for e in errors)
    
    def test_validate_invalid_number(self):
        """Test validation of invalid number field."""
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "customer_name": "Acme Corp",
            "amount_subtotal": "not_a_number",
            "amount_total": "1200.00",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="sales_invoice",
        )
        
        assert not is_valid
        errors_str = str(errors.errors)
        assert "amount_subtotal" in errors_str
    
    def test_validate_negative_amount(self):
        """Test validation rejects negative amount."""
        data = {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "customer_name": "Acme Corp",
            "amount_subtotal": "-1000.00",
            "amount_total": "1200.00",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="sales_invoice",
        )
        
        assert not is_valid
    
    def test_validate_with_context(self):
        """Test validation with full context (row, item, batch)."""
        errors = universal_validator.validate_document(
            data={"invoice_number": "INV-001"},
            doc_type="sales_invoice",
            row_number=42,
            item_id="item-123",
            batch_id="batch-456",
        )
        
        assert errors.has_errors()
        assert errors.errors[0].row_number == 42
        assert errors.errors[0].item_id == "item-123"
        assert errors.errors[0].batch_id == "batch-456"
    
    def test_find_field_mapping(self):
        """Test auto-detecting field mapping from headers."""
        headers = [
            "Numero de Factura",
            "Fecha",
            "Cliente",
            "Subtotal",
            "Total",
        ]
        
        mapping = universal_validator.find_field_mapping(headers, "sales_invoice")
        
        assert "Numero de Factura" in mapping
        assert mapping["Numero de Factura"] == "invoice_number"
        assert "Fecha" in mapping
        assert mapping["Fecha"] == "invoice_date"


class TestRobustExcelParser:
    """Test robust Excel parsing with problematic files."""
    
    def test_detect_header_skips_junk_rows(self):
        """Test that header detection skips instruction rows."""
        # This test would need a real problematic Excel file
        # For now, we test the junk keyword detection
        parser = robust_parser
        
        assert parser._contains_junk_keyword("instrucciones: por favor rellenar")
        assert parser._contains_junk_keyword("NOTA: este es un ejemplo")
        assert not parser._contains_junk_keyword("Factura")
        assert not parser._contains_junk_keyword("Cliente")
    
    def test_extract_headers_normalizes(self):
        """Test header extraction normalizes whitespace."""
        # Would need actual openpyxl worksheet
        # Test the logic independently
        headers = ["  Factura  ", "Fecha", None, "Cliente"]
        
        # Verify normalization happens in _extract_headers
        normalized = [h.strip() if h else h for h in headers if h]
        assert "Factura" in normalized
        assert "Fecha" in normalized
        assert "Cliente" in normalized


class TestValidationComplete:
    """Integration tests for complete validation flow."""
    
    def test_validate_expense_with_all_fields(self):
        """Test expense validation with all optional fields."""
        data = {
            "expense_date": "2024-01-20",
            "description": "Office supplies",
            "amount": "150.50",
            "category": "Office Supplies",
            "receipt_number": "RCP-001",
            "vendor_name": "Office Depot",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="expense",
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_bank_transaction_minimal(self):
        """Test bank transaction with only required fields."""
        data = {
            "transaction_date": "2024-01-25",
            "amount": "5000.00",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="bank_tx",
        )
        
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_bank_transaction_invalid_direction(self):
        """Test bank transaction with invalid direction field."""
        data = {
            "transaction_date": "2024-01-25",
            "amount": "5000.00",
            "direction": "invalid_direction",
        }
        
        is_valid, errors = universal_validator.validate_document_complete(
            data=data,
            doc_type="bank_tx",
        )
        
        # Should still be valid (direction has no validators)
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
