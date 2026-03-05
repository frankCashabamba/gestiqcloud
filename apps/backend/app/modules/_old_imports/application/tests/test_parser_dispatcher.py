from pathlib import Path

import pytest


def _build_excel(tmp_path: Path, headers: list[str], rows: list[list[str]]) -> Path:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    dest = tmp_path / "sample.xlsx"
    wb.save(dest)
    return dest


def test_dispatcher_picks_bank_for_xlsx(tmp_path):
    from app.modules.imports.parsers.dispatcher import select_parser_for_file

    path = _build_excel(
        tmp_path,
        ["Fecha", "Valor", "Importe", "Concepto", "IBAN"],
        [["2024-01-01", "2024-01-02", -10.5, "Pago", "ES12"]],
    )
    parser_id, doc_type = select_parser_for_file(str(path))
    assert parser_id == "xlsx_bank"
    assert doc_type == "bank_transactions"


def test_dispatcher_picks_invoices_for_xlsx(tmp_path):
    from app.modules.imports.parsers.dispatcher import select_parser_for_file

    path = _build_excel(
        tmp_path,
        ["Factura", "Fecha", "Proveedor", "Subtotal", "IVA", "Total"],
        [["F-1", "2024-01-01", "ACME", 100, 12, 112]],
    )
    parser_id, doc_type = select_parser_for_file(str(path))
    assert parser_id == "xlsx_invoices"
    assert doc_type == "invoices"
