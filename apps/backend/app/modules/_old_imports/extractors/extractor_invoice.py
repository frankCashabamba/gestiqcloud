from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractors.utilities import (
    is_valid_concept,
    search_amount,
    search_client,
    search_concept,
    search_date,
    search_description,
    search_invoice_number,
    search_issuer,
    search_largest_number,
    search_subtotal,
    search_tax_id,
)


def extract_invoice(text: str, country: str = "EC") -> list[dict[str, Any]]:
    """
    Extracts invoice data and returns canonical schema.

    Args:
        text: OCR text of the document
        country: Document country (EC, ES, etc.)

    Returns:
        List with a CanonicalDocument of type "invoice"
    """
    try:
        date = search_date(text)
        number = search_invoice_number(text)
        tax_id = search_tax_id(text)

        total_raw = search_amount(text) or search_largest_number(text) or "0.00"
        try:
            total = float(total_raw.replace(",", "."))
        except Exception:
            total = 0.0

        subtotal_raw = search_subtotal(text)
        subtotal = 0.0
        if subtotal_raw:
            try:
                subtotal = float(subtotal_raw.strip().replace(",", "."))
            except Exception:
                subtotal = total

        description = search_description(text)
        concept = search_concept(text)
        issuer = search_issuer(text)
        client = search_client(text)

        final_concept = concept or description or ""
        if not is_valid_concept(final_concept):
            final_concept = "Document without concept"

        # Build canonical schema
        tax = total - subtotal if subtotal > 0 else 0.0

        canonical: CanonicalDocument = {
            "doc_type": "invoice",
            "country": country,
            "currency": "USD" if country == "EC" else "EUR",
            "issue_date": date or None,
            "invoice_number": number,
            "vendor": {
                "name": issuer or "Unknown vendor",
                "tax_id": tax_id,
                "country": country,
            },
            "buyer": {
                "name": client or "Unknown client",
            },
            "totals": {
                "subtotal": subtotal,
                "tax": tax,
                "total": total,
                "tax_breakdown": (
                    [
                        {
                            "rate": 12.0 if country == "EC" else 21.0,
                            "amount": tax,
                            "code": f"IVA{12 if country == 'EC' else 21}-{country}",
                            "base": subtotal,
                        }
                    ]
                    if tax > 0
                    else []
                ),
            },
            "lines": [
                {
                    "desc": final_concept,
                    "qty": 1.0,
                    "unit_price": total,
                    "total": total,
                    "tax_code": f"IVA{12 if country == 'EC' else 21}",
                    "tax_amount": tax,
                }
            ],
            "source": "ocr",
            "confidence": 0.7,  # Medium confidence for OCR
        }

        # Add routing proposal
        canonical["routing_proposal"] = build_routing_proposal(
            canonical,
            category_code="OTROS",
            account="6290",  # General expenses account
            confidence=0.65,
        )

        return [canonical]

    except Exception as e:
        print("Error in extract_invoice:", e)
        return []
