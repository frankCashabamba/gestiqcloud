import textwrap
from pathlib import Path


def test_parse_csv_bank(tmp_path):
    from app.modules.imports.parsers.csv_bank import parse_csv_bank

    csv_content = "transaction_date,value_date,amount,concepto,iban,currency\n2024-01-01,2024-01-02,-12.5,Compra,ES12,EUR\n"
    path = tmp_path / "bank.csv"
    path.write_text(csv_content, encoding="utf-8")

    result = parse_csv_bank(str(path))
    assert result["rows_parsed"] == 1
    tx = result["bank_transactions"][0]
    assert tx["doc_type"] == "bank_tx"
    assert tx["bank_tx"]["amount"] == 12.5
    assert tx["bank_tx"]["direction"] == "debit"


def test_parse_csv_invoices(tmp_path):
    from app.modules.imports.parsers.csv_invoices import parse_csv_invoices

    csv_content = "invoice_number,invoice_date,vendor,buyer,subtotal,tax,total,currency\nF-1,2024-01-01,ACME,Cliente,100,12,112,USD\n"
    path = tmp_path / "inv.csv"
    path.write_text(csv_content, encoding="utf-8")

    result = parse_csv_invoices(str(path))
    assert result["rows_parsed"] == 1
    inv = result["invoices"][0]
    assert inv["doc_type"] == "invoice"
    assert inv["invoice_number"] == "F-1"
    assert inv["totals"]["total"] == 112


def test_parse_xml_invoice_generic(tmp_path):
    from app.modules.imports.parsers.xml_invoice import parse_xml_invoice

    xml = textwrap.dedent(
        """\
        <Invoice>
          <invoice_number>INV-1</invoice_number>
          <date>2024-01-01</date>
          <vendor_name>ACME</vendor_name>
        </Invoice>
        """
    )
    path = tmp_path / "invoice.xml"
    path.write_text(xml, encoding="utf-8")

    result = parse_xml_invoice(str(path))
    assert result["rows_parsed"] == 1
    inv = result["invoices"][0]
    assert inv["doc_type"] == "invoice"
    assert inv["invoice_number"] == "INV-1"


def test_parse_xml_camt053(tmp_path):
    from app.modules.imports.parsers.xml_camt053_bank import parse_xml_camt053_bank

    xml = textwrap.dedent(
        """\
        <Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
          <BkToCstmrStmt>
            <Stmt>
              <Ntry>
                <BookgDt><Dt>2024-01-01</Dt></BookgDt>
                <ValDt><Dt>2024-01-02</Dt></ValDt>
                <Amt Ccy="EUR">-25.0</Amt>
                <CdtDbtInd>DBIT</CdtDbtInd>
                <RmtInf><Ustrd>Pago</Ustrd></RmtInf>
                <AcctSvcrRef>REF1</AcctSvcrRef>
                <IBAN>ES1200</IBAN>
              </Ntry>
            </Stmt>
          </BkToCstmrStmt>
        </Document>
        """
    )
    path = tmp_path / "camt.xml"
    path.write_text(xml, encoding="utf-8")

    result = parse_xml_camt053_bank(str(path))
    assert result["rows_parsed"] == 1
    tx = result["bank_transactions"][0]
    assert tx["doc_type"] == "bank_tx"
    assert tx["bank_tx"]["amount"] == 25.0
