"""
Parser para facturas electrónicas españolas en formato Facturae.

Soporta:
- Facturae 3.2.x (namespace http://www.facturae.gob.es/formato)

Salida: dict con rows, headers, metadata compatible con el resto de parsers.
"""

import xml.etree.ElementTree as ET
from typing import Any


FACTURAE_NS = "http://www.facturae.gob.es/formato"


def parse_facturae(file_path: str) -> dict[str, Any]:
    """
    Analiza un archivo de factura en formato Facturae español.

    Args:
        file_path: Ruta al archivo XML

    Returns:
        Dict con rows, headers, metadata y detected_type
    """
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    metadata: dict[str, Any] = {}

    try:
        root = _parse_facturae_xml(file_path)

        ns = {"fe": FACTURAE_NS}

        if not root.tag.endswith("Facturae") and FACTURAE_NS not in root.tag:
            errors.append("El archivo no es un documento Facturae válido")
            return _build_error_response(errors)

        metadata["file_header"] = _extract_file_header(root, ns)
        metadata["seller"] = _extract_party(root, ns, "SellerParty")
        metadata["buyer"] = _extract_party(root, ns, "BuyerParty")

        invoices = root.findall(".//fe:Invoices/fe:Invoice", ns)
        if not invoices:
            invoices = root.findall(".//{%s}Invoice" % FACTURAE_NS)

        for invoice in invoices:
            invoice_data = _extract_invoice(invoice, ns)
            metadata["invoice_number"] = invoice_data.get("invoice_number")
            metadata["invoice_series"] = invoice_data.get("invoice_series")
            metadata["issue_date"] = invoice_data.get("issue_date")
            metadata["totals"] = invoice_data.get("totals", {})

            for item in invoice_data.get("items", []):
                rows.append(item)

    except ET.ParseError as e:
        errors.append(f"Error parsing XML: {str(e)}")
    except Exception as e:
        errors.append(f"Error inesperado: {str(e)}")

    if errors:
        return _build_error_response(errors)

    headers = [
        "description",
        "quantity",
        "unit_price",
        "amount",
        "tax_rate",
        "tax_amount",
    ]

    return {
        "rows": rows,
        "headers": headers,
        "metadata": metadata,
        "detected_type": "invoices",
        "parser": "xml_facturae",
        "source_type": "xml",
        "rows_processed": len(rows),
        "rows_parsed": len(rows),
        "errors": errors,
    }


def _parse_facturae_xml(file_path: str) -> ET.Element:
    """
    Parsea el XML de Facturae, manejando el caso de elementos adicionales
    después del cierre del documento (como Signature fuera de Facturae).
    """
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except ET.ParseError as e:
        if "junk after document element" in str(e):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            end_tag = "</Facturae>"
            idx = content.find(end_tag)
            if idx != -1:
                clean_content = content[: idx + len(end_tag)]
                return ET.fromstring(clean_content)
        raise


def _build_error_response(errors: list[str]) -> dict[str, Any]:
    return {
        "rows": [],
        "headers": [],
        "metadata": {},
        "detected_type": "invoices",
        "parser": "xml_facturae",
        "source_type": "xml",
        "rows_processed": 0,
        "rows_parsed": 0,
        "errors": errors,
    }


def _extract_file_header(root: ET.Element, ns: dict) -> dict[str, Any]:
    header = root.find(".//fe:FileHeader", ns)
    if header is None:
        header = root.find(".//{%s}FileHeader" % FACTURAE_NS)

    if header is None:
        return {}

    return {
        "schema_version": _find_text(header, "fe:SchemaVersion", ns),
        "modality": _find_text(header, "fe:Modality", ns),
        "invoice_issuer_type": _find_text(header, "fe:InvoiceIssuerType", ns),
    }


def _extract_party(root: ET.Element, ns: dict, party_type: str) -> dict[str, Any]:
    party = root.find(f".//fe:Parties/fe:{party_type}", ns)
    if party is None:
        party = root.find(".//{%s}%s" % (FACTURAE_NS, party_type))

    if party is None:
        return {}

    legal_entity = party.find(".//fe:LegalEntity", ns)
    if legal_entity is None:
        legal_entity = party.find(".//{%s}LegalEntity" % FACTURAE_NS)

    individual = party.find(".//fe:Individual", ns)
    if individual is None:
        individual = party.find(".//{%s}Individual" % FACTURAE_NS)

    tax_id_elem = party.find(".//fe:TaxIdentification", ns)
    if tax_id_elem is None:
        tax_id_elem = party.find(".//{%s}TaxIdentification" % FACTURAE_NS)

    result: dict[str, Any] = {}

    if tax_id_elem is not None:
        result["tax_id"] = _find_text(tax_id_elem, "fe:TaxIdentificationNumber", ns)
        result["person_type"] = _find_text(tax_id_elem, "fe:PersonTypeCode", ns)
        result["residence_type"] = _find_text(tax_id_elem, "fe:ResidenceTypeCode", ns)

    if legal_entity is not None:
        result["name"] = _find_text(legal_entity, "fe:CorporateName", ns)
        result["trade_name"] = _find_text(legal_entity, "fe:TradeName", ns)
        address = legal_entity.find(".//fe:AddressInSpain", ns)
        if address is None:
            address = legal_entity.find(".//{%s}AddressInSpain" % FACTURAE_NS)
        if address is not None:
            result["address"] = {
                "street": _find_text(address, "fe:Address", ns),
                "post_code": _find_text(address, "fe:PostCode", ns),
                "town": _find_text(address, "fe:Town", ns),
                "province": _find_text(address, "fe:Province", ns),
                "country": _find_text(address, "fe:CountryCode", ns),
            }
    elif individual is not None:
        result["name"] = " ".join(
            filter(
                None,
                [
                    _find_text(individual, "fe:Name", ns),
                    _find_text(individual, "fe:FirstSurname", ns),
                    _find_text(individual, "fe:SecondSurname", ns),
                ],
            )
        )

    return result


def _extract_invoice(invoice: ET.Element, ns: dict) -> dict[str, Any]:
    header = invoice.find(".//fe:InvoiceHeader", ns)
    if header is None:
        header = invoice.find(".//{%s}InvoiceHeader" % FACTURAE_NS)

    issue_data = invoice.find(".//fe:InvoiceIssueData", ns)
    if issue_data is None:
        issue_data = invoice.find(".//{%s}InvoiceIssueData" % FACTURAE_NS)

    totals_elem = invoice.find(".//fe:InvoiceTotals", ns)
    if totals_elem is None:
        totals_elem = invoice.find(".//{%s}InvoiceTotals" % FACTURAE_NS)

    result: dict[str, Any] = {
        "invoice_number": None,
        "invoice_series": None,
        "issue_date": None,
        "totals": {},
        "items": [],
    }

    if header is not None:
        result["invoice_number"] = _find_text(header, "fe:InvoiceNumber", ns)
        result["invoice_series"] = _find_text(header, "fe:InvoiceSeriesCode", ns)
        result["document_type"] = _find_text(header, "fe:InvoiceDocumentType", ns)
        result["invoice_class"] = _find_text(header, "fe:InvoiceClass", ns)

    if issue_data is not None:
        result["issue_date"] = _find_text(issue_data, "fe:IssueDate", ns)

    if totals_elem is not None:
        result["totals"] = {
            "gross_amount": _to_float(_find_text(totals_elem, "fe:TotalGrossAmount", ns)),
            "general_discounts": _to_float(
                _find_text(totals_elem, "fe:TotalGeneralDiscounts", ns)
            ),
            "general_surcharges": _to_float(
                _find_text(totals_elem, "fe:TotalGeneralSurcharges", ns)
            ),
            "total_gross_before_taxes": _to_float(
                _find_text(totals_elem, "fe:TotalGrossAmountBeforeTaxes", ns)
            ),
            "total_tax_outputs": _to_float(
                _find_text(totals_elem, "fe:TotalTaxOutputs", ns)
            ),
            "total_tax_withheld": _to_float(
                _find_text(totals_elem, "fe:TotalTaxesWithheld", ns)
            ),
            "invoice_total": _to_float(_find_text(totals_elem, "fe:InvoiceTotal", ns)),
            "total_payable": _to_float(
                _find_text(totals_elem, "fe:TotalOutstandingAmount", ns)
            ),
            "total_executable": _to_float(
                _find_text(totals_elem, "fe:TotalExecutableAmount", ns)
            ),
        }

    items_elem = invoice.find(".//fe:Items", ns)
    if items_elem is None:
        items_elem = invoice.find(".//{%s}Items" % FACTURAE_NS)

    if items_elem is not None:
        for line in items_elem.findall("fe:InvoiceLine", ns):
            if line is None:
                for line in items_elem.findall("{%s}InvoiceLine" % FACTURAE_NS):
                    result["items"].append(_extract_line(line, ns))
            else:
                result["items"].append(_extract_line(line, ns))

    return result


def _extract_line(line: ET.Element, ns: dict) -> dict[str, Any]:
    tax_elem = line.find(".//fe:TaxesOutputs/fe:Tax", ns)
    if tax_elem is None:
        tax_elem = line.find(".//{%s}Tax" % FACTURAE_NS)

    tax_rate = None
    tax_amount = None
    if tax_elem is not None:
        tax_rate = _to_float(_find_text(tax_elem, "fe:TaxRate", ns))
        tax_amount_elem = tax_elem.find(".//fe:TaxAmount/fe:TotalAmount", ns)
        if tax_amount_elem is None:
            tax_amount_elem = tax_elem.find(".//{%s}TaxAmount/{%s}TotalAmount" % (FACTURAE_NS, FACTURAE_NS))
        if tax_amount_elem is not None:
            tax_amount = _to_float(tax_amount_elem.text)

    return {
        "description": _find_text(line, "fe:ItemDescription", ns),
        "quantity": _to_float(_find_text(line, "fe:Quantity", ns)),
        "unit_price": _to_float(_find_text(line, "fe:UnitPriceWithoutTax", ns)),
        "amount": _to_float(_find_text(line, "fe:TotalAmountWithoutTax", ns)),
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
    }


def _find_text(elem: ET.Element, path: str, ns: dict) -> str | None:
    found = elem.find(path, ns)
    if found is not None and found.text:
        return found.text.strip()
    path_no_ns = path.replace("fe:", "{%s}" % FACTURAE_NS)
    found = elem.find(path_no_ns)
    if found is not None and found.text:
        return found.text.strip()
    return None


def _to_float(val: str | None) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val.replace(",", "."))
    except (ValueError, TypeError):
        return None


def can_parse(file_path: str) -> bool:
    """Verifica si el archivo es un Facturae válido."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        return FACTURAE_NS in root.tag or root.tag.endswith("Facturae")
    except Exception:
        return False
