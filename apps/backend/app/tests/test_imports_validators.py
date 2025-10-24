from app.modules.imports.validators import validate_invoices, validate_bank, validate_expenses


def test_validate_invoices_ok_and_error():
    ok = {
        "invoice_number": "F-1",
        "invoice_date": "01/02/2024",
        "net_amount": 100.0,
        "tax_amount": 21.0,
        "total_amount": 121.0,
        "currency": "EUR",
    }
    assert validate_invoices(ok) == []

    bad = {
        "invoice_number": "F-2",
        "invoice_date": "2024-02-01",
        "net_amount": 10.0,
        "tax_amount": 2.0,
        "total_amount": 20.0,  # mismatch
        "currency": "EURO",    # invalid
    }
    errs = validate_invoices(bad)
    fields = {e["field"] for e in errs}
    assert "total_amount" in fields
    assert "currency" in fields


def test_validate_bank_ok_and_refs():
    ok = {"transaction_date": "2024-02-01", "amount": 10}
    assert validate_bank(ok) == []

    with_refs = {"transaction_date": "2024-02-01", "amount": 10, "statement_id": " ", "entry_ref": ""}
    errs = validate_bank(with_refs)
    fields = {e["field"] for e in errs}
    assert "statement_id" in fields and "entry_ref" in fields


def test_validate_expenses_category_policy():
    base = {"expense_date": "2024-01-01", "amount": 5}
    assert validate_expenses(base) == []
    errs = validate_expenses(base, require_categories=True)
    assert any(e["field"] == "category" for e in errs)

