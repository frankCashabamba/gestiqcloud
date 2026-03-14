from __future__ import annotations

from decimal import Decimal
from typing import Any


def generate_facturae_xml(invoice_data: dict[str, Any]) -> str:
    """
    Generar XML Facturae conforme a especificacion espanola.
    Version simplificada para MVP.
    """
    from lxml import etree

    def _normalize_rate(raw: Any) -> Decimal:
        try:
            rate = Decimal(str(raw)) if raw is not None else Decimal("0")
        except Exception:
            return Decimal("0")
        if rate > 1:
            rate = rate / Decimal("100")
        if rate < 0:
            rate = Decimal("0")
        return rate

    def _resolve_rate() -> Decimal:
        raw = invoice_data.get("tax_rate") or invoice_data.get("iva_rate")
        if raw is not None:
            return _normalize_rate(raw)
        subtotal = Decimal(str(invoice_data.get("subtotal") or 0))
        iva = Decimal(str(invoice_data.get("iva") or 0))
        if subtotal <= 0:
            return Decimal("0")
        return _normalize_rate(iva / subtotal)

    tax_rate = _resolve_rate()
    tax_rate_pct = (tax_rate * Decimal("100")).quantize(Decimal("0.01"))

    root = etree.Element(
        "facturae",
        nsmap={
            None: "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
        },
    )
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")

    file_header = etree.SubElement(root, "FileHeader")
    etree.SubElement(file_header, "SchemaVersion").text = "3.2"
    etree.SubElement(file_header, "Modality").text = "I"
    etree.SubElement(file_header, "InvoiceIssuerType").text = "EM"

    parties = etree.SubElement(root, "Parties")

    seller = etree.SubElement(parties, "SellerParty")
    tax_id_seller = etree.SubElement(seller, "TaxIdentification")
    etree.SubElement(tax_id_seller, "PersonTypeCode").text = "J"
    etree.SubElement(tax_id_seller, "ResidenceTypeCode").text = "R"
    etree.SubElement(tax_id_seller, "TaxIdentificationNumber").text = invoice_data["empresa"]["ruc"]

    buyer = etree.SubElement(parties, "BuyerParty")
    tax_id_buyer = etree.SubElement(buyer, "TaxIdentification")
    etree.SubElement(tax_id_buyer, "PersonTypeCode").text = "J"
    etree.SubElement(tax_id_buyer, "ResidenceTypeCode").text = "R"
    etree.SubElement(tax_id_buyer, "TaxIdentificationNumber").text = invoice_data["cliente"]["ruc"]

    invoices = etree.SubElement(root, "Invoices")
    invoice = etree.SubElement(invoices, "Invoice")

    header = etree.SubElement(invoice, "InvoiceHeader")
    etree.SubElement(header, "InvoiceNumber").text = invoice_data["numero"]
    etree.SubElement(header, "InvoiceSeriesCode").text = "A"
    etree.SubElement(header, "InvoiceDocumentType").text = "FC"
    etree.SubElement(header, "InvoiceClass").text = "OO"

    issue_data = etree.SubElement(invoice, "InvoiceIssueData")
    etree.SubElement(issue_data, "IssueDate").text = invoice_data["fecha"].strftime("%Y-%m-%d")

    taxes = etree.SubElement(invoice, "TaxesOutputs")
    tax = etree.SubElement(taxes, "Tax")
    etree.SubElement(tax, "TaxTypeCode").text = "01"
    etree.SubElement(tax, "TaxRate").text = f"{tax_rate_pct:.2f}"
    etree.SubElement(tax, "TaxableBase").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(tax, "TaxAmount").text = f"{invoice_data['iva']:.2f}"

    totals = etree.SubElement(invoice, "InvoiceTotals")
    etree.SubElement(totals, "TaxOutputsTotal").text = f"{invoice_data['iva']:.2f}"
    etree.SubElement(totals, "TotalGrossAmount").text = f"{invoice_data['total']:.2f}"
    etree.SubElement(totals, "TotalGrossAmountBeforeTaxes").text = f"{invoice_data['subtotal']:.2f}"
    etree.SubElement(totals, "TotalTaxesOutputs").text = f"{invoice_data['iva']:.2f}"
    etree.SubElement(totals, "TotalExecutableAmount").text = f"{invoice_data['total']:.2f}"

    return etree.tostring(root, encoding="unicode", pretty_print=True)
