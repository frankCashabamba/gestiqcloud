#!/usr/bin/env python3
"""Quick validation of P0 implementation."""

import sys

sys.path.insert(0, "./apps/backend")

from app.modules.imports.domain.canonical_schema import DocumentType, get_schema
from app.modules.imports.domain.errors import ErrorCategory, ImportError, ImportErrorCollection
from app.modules.imports.domain.validator import universal_validator

# from app.modules.imports.parsers.robust_excel import robust_parser  # Will test separately


def test_canonical_schemas():
    """Test schema retrieval."""
    print("[OK] Testing canonical schemas...")

    sales = get_schema("sales_invoice")
    assert sales is not None
    assert sales.doc_type == DocumentType.SALES_INVOICE
    assert "invoice_number" in sales.fields
    print("  [OK] Sales invoice schema OK")

    purchase = get_schema("purchase_invoice")
    assert purchase is not None
    print("  [OK] Purchase invoice schema OK")

    expense = get_schema("expense")
    assert expense is not None
    assert "expense_date" in expense.fields
    print("  [OK] Expense schema OK")

    bank = get_schema("bank_tx")
    assert bank is not None
    print("  [OK] Bank transaction schema OK")


def test_structured_errors():
    """Test error structure."""
    print("\n[OK] Testing structured errors...")

    error = ImportError(
        row_number=10,
        field_name="amount",
        canonical_field="amount_total",
        category=ErrorCategory.VALIDATION,
        message="Amount must be positive",
        suggestion="Ensure value > 0",
        raw_value="-100",
    )

    assert error.row_number == 10
    assert error.field_name == "amount"
    assert error.message == "Amount must be positive"
    print("  [OK] ImportError creation OK")

    # Test error dict conversion
    error_dict = error.to_dict()
    assert error_dict["row_number"] == 10
    assert error_dict["category"] == "validation"
    print("  [OK] Error serialization OK")

    # Test error collection
    errors = ImportErrorCollection()
    errors.add("Error 1", row_number=1, field_name="field1")
    errors.add("Error 2", row_number=2, field_name="field2")
    assert len(errors) == 2
    print("  [OK] Error collection OK")


def test_validation():
    """Test document validation."""
    print("\n[OK] Testing universal validator...")

    # Valid sales invoice
    valid_data = {
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "customer_name": "Acme Corp",
        "amount_subtotal": "1000.00",
        "amount_total": "1200.00",
    }

    is_valid, errors = universal_validator.validate_document_complete(
        data=valid_data,
        doc_type="sales_invoice",
    )
    assert is_valid
    assert len(errors) == 0
    print("  [OK] Valid invoice validation OK")

    # Missing required field
    invalid_data = {
        "invoice_number": "INV-001",
        # Missing invoice_date
        "customer_name": "Acme Corp",
        "amount_subtotal": "1000.00",
        "amount_total": "1200.00",
    }

    is_valid, errors = universal_validator.validate_document_complete(
        data=invalid_data,
        doc_type="sales_invoice",
    )
    assert not is_valid
    assert len(errors) > 0
    print("  [OK] Invalid invoice validation OK")

    # Field mapping
    headers = ["Numero de Factura", "Fecha", "Cliente", "Subtotal", "Total"]
    mapping = universal_validator.find_field_mapping(headers, "sales_invoice")
    assert "Numero de Factura" in mapping
    assert mapping["Numero de Factura"] == "invoice_number"
    print("  [OK] Field mapping detection OK")


def test_robust_parser():
    """Test robust Excel parser basics."""
    print("\n[OK] Testing robust Excel parser...")
    print("  (Will be tested in full integration suite with openpyxl installed)")


if __name__ == "__main__":
    try:
        test_canonical_schemas()
        test_structured_errors()
        test_validation()
        test_robust_parser()
        print("\n" + "=" * 50)
        print("[OK] ALL P0 TESTS PASSED")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
