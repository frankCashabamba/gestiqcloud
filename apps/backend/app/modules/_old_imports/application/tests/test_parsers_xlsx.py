import pytest


def test_parse_xlsx_bank(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from app.modules.imports.parsers.xlsx_bank import parse_xlsx_bank

    # Build minimal workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Fecha", "Valor", "Importe", "Concepto", "IBAN", "Moneda"])
    ws.append(["2024-01-01", "2024-01-02", -10.5, "Pago", "ES12", "EUR"])
    path = tmp_path / "bank.xlsx"
    wb.save(path)

    result = parse_xlsx_bank(str(path))
    assert result["rows_parsed"] == 1
    tx = result["bank_transactions"][0]
    assert tx["doc_type"] == "bank_tx"
    assert tx["bank_tx"]["amount"] == 10.5
    assert tx["bank_tx"]["direction"] == "debit"


def test_parse_xlsx_invoices(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from app.modules.imports.parsers.xlsx_invoices import parse_xlsx_invoices

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Factura", "Fecha", "Proveedor", "Subtotal", "IVA", "Total", "Moneda"])
    ws.append(["F-1", "2024-01-01", "ACME", 100, 12, 112, "USD"])
    path = tmp_path / "inv.xlsx"
    wb.save(path)

    result = parse_xlsx_invoices(str(path))
    assert result["rows_parsed"] == 1
    inv = result["invoices"][0]
    assert inv["doc_type"] == "invoice"
    assert inv["invoice_number"] == "F-1"
    assert inv["totals"]["total"] == 112
