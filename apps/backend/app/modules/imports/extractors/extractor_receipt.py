import re
from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractors.utilities import search_multiple, is_valid_concept


def extract_receipt(text: str, country: str = "EC") -> list[dict[str, Any]]:
    """
    Extracts receipt/ticket data and returns canonical schema.

    Args:
        text: OCR text of the document
        country: Document country (EC, ES, etc.)

    Returns:
        List with a CanonicalDocument of type "expense_receipt"
    """
    # Basic text cleaning
    text = text.replace("€", "EUR").replace("$", "USD")
    text = re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove strange characters

    # Payment date
    date = search_multiple(
        [
            r"Date\s*paid[:\-]?\s*(\w+\s+\d{1,2},?\s+\d{4})",
            r"paid\s*on\s*(\w+\s+\d{1,2},?\s+\d{4})",
            r"\b(\d{2}/\d{2}/\d{4})\b",
            r"\b(\d{2}-\d{2}-\d{4})\b",
            r"(\d{4}-\d{2}-\d{2})",
        ],
        text,
    )

    # Paid amount
    amount_str = (
        search_multiple(
            [
                r"Amount\s*paid[^0-9]*([\d]{1,4}[.,]\d{2})",
                r"Total[:;\s]*([\d]{1,4}[.,]\d{2})",
                r"([\d]{1,4}[.,]\d{2})\s*(USD|EUR)?",
            ],
            text,
        )
        or "0.00"
    )

    amount = float(amount_str.replace(",", "."))

    # Client/Vendor
    client = (
        search_multiple(
            [
                r"Bill\s*to\s+([^\s@]+@[^\s]+)",
                r"Bill\s*to[:;\s]*\n?(.+)",
                r"Cliente[:;\s]*(.+)",
                r"CDAD\.?\s+(.{3,80})",
                r"([A-Z][A-Za-z]+ [A-Z][A-Za-z]+)",
            ],
            text,
        )
        or "unknown"
    )

    # Concept
    concept = search_multiple(
        [
            r"(CUOTA\s+[A-Z]{3,}\.?\s*/?\s*\d{4})",
            r"(SERVICIOS\s+[^\n]{3,80})",
            r"(ALQUILER\s+[^\n]{3,80})",
            r"Description\s+Qty\s+Unit price\s+Amount\s+([\s\S]{10,100})",
            r"(Servers[^\n]{0,80})",
            r"(Postgres[^\n]{0,80})",
        ],
        text,
    )

    concept_raw = concept or ""
    final_concept = concept_raw if is_valid_concept(concept_raw) else "Document without concept"

    # Build canonical schema
    subtotal = amount
    tax = 0.0

    canonical: CanonicalDocument = {
        "doc_type": "expense_receipt",
        "country": country,
        "currency": "USD" if country == "EC" else "EUR",
        "issue_date": date or None,
        "vendor": {
            "name": client,
        },
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": amount,
            "tax_breakdown": [],
        },
        "lines": [
            {
                "desc": final_concept,
                "qty": 1.0,
                "unit_price": amount,
                "total": amount,
                "tax_code": f"IVA{12 if country == 'EC' else 21}",
            }
        ],
        "payment": {
            "method": "cash",  # Assumes cash by default for receipts
        },
        "source": "ocr",
        "confidence": 0.6,
    }

    # Routing proposal
    canonical["routing_proposal"] = build_routing_proposal(
        canonical, category_code="OTROS", account="6290", confidence=0.60
    )

    return [canonical]
