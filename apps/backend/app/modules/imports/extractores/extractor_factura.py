import re
from typing import Any

from app.modules.imports.domain.canonical_schema import CanonicalDocument, build_routing_proposal
from app.modules.imports.extractores.utilidades import (
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


def _to_float_locale(value: str | None) -> float:
    if not value:
        return 0.0
    s = str(value).strip().replace(" ", "")
    if "," in s and "." in s:
        # 2,145.00 -> 2145.00 / 2.145,00 -> 2145.00
        if s.rfind(".") > s.rfind(","):
            s = s.replace(",", "")
        else:
            s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0


def _find_labeled_total(text: str) -> float:
    # Common labels in EC invoices
    patterns = [
        r"VALOR\s+TOTAL\s*[:\-]?\s*([0-9][0-9.,]*)",
        r"TOTAL\s+A\s+PAGAR\s*[:\-]?\s*([0-9][0-9.,]*)",
        r"TOTAL\s*[:\-]?\s*([0-9][0-9.,]*)",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            val = _to_float_locale(m.group(1))
            if val > 0:
                return val
    return 0.0


def _find_tax_rate(text: str, *, default_rate: float | None = None) -> float | None:
    # IVA 15% / IVA: 15 %
    m = re.search(r"\bIVA\s*[:\-]?\s*(\d{1,2})\s*%\b", text, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    # SUB TOTAL 15 %
    m = re.search(r"\bSUB\s*TOTAL\s*(\d{1,2})\s*%\b", text, flags=re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            pass
    return default_rate


def _extract_invoice_lines(text: str) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    # Example OCR line (EC invoices):
    # PT-HARINA-00006 0788... 50.00 HARINA ... 42.90 2,145.00
    patterns = [
        # qty at start
        r"^\s*(\d+(?:[.,]\d+)?)\s+(.{6,}?)\s+(\d+(?:[.,]\d+)?)\s+(\d[\d.,]*)\b",
        # allow up to 3 leading tokens (codes/barcodes)
        r"(?:\S+\s+){0,3}(\d+(?:[.,]\d+)?)\s+(.{6,}?)\s+(\d+(?:[.,]\d+)?)\s+(\d[\d.,]*)\b",
    ]

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if len(line) < 12:
            continue
        # Skip header-ish rows
        if re.search(r"\b(codigo|cantidad|descripcion|p/?unit|precio)\b", line, re.IGNORECASE):
            continue

        m = None
        for pat in patterns:
            m = re.search(pat, line, flags=re.IGNORECASE)
            if m:
                break
        if not m:
            continue

        qty = _to_float_locale(m.group(1))
        desc = m.group(2).strip()
        unit_price = _to_float_locale(m.group(3))
        total = _to_float_locale(m.group(4))

        # Basic sanity: require some letters in description
        if not re.search(r"[A-Za-z]", desc):
            continue
        if qty <= 0 and total <= 0:
            continue

        lines.append(
            {
                "desc": desc,
                "qty": qty if qty > 0 else 1.0,
                "unit_price": unit_price,
                "total": total if total > 0 else unit_price,
            }
        )

    return lines


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

        total = _find_labeled_total(text)
        if total <= 0:
            total_raw = search_amount(text) or search_largest_number(text) or "0.00"
            total = _to_float_locale(total_raw)

        subtotal_raw = search_subtotal(text)
        subtotal = _to_float_locale(subtotal_raw)

        description = search_description(text)
        concept = search_concept(text)
        issuer = search_issuer(text)
        client = search_client(text)
        extracted_lines = _extract_invoice_lines(text)
        if extracted_lines:
            computed_total = sum(float(line.get("total") or 0) for line in extracted_lines)
            if total <= 0 and computed_total > 0:
                total = computed_total

        final_concept = concept or description or ""
        if (not final_concept or final_concept.lower() == "renta") and extracted_lines:
            final_concept = str(extracted_lines[0].get("desc") or "")
        if not is_valid_concept(final_concept):
            final_concept = "Document without concept"

        # Build canonical schema
        if subtotal <= 0 and total > 0:
            subtotal = total
        tax = max(total - subtotal, 0.0) if subtotal > 0 else 0.0
        tax_rate = _find_tax_rate(text, default_rate=(15.0 if country == "EC" else 21.0))
        tax_code = (
            f"IVA{int(tax_rate)}"
            if tax_rate is not None
            else (f"IVA{15 if country == 'EC' else 21}")
        )

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
                            "rate": float(tax_rate)
                            if tax_rate is not None
                            else (15.0 if country == "EC" else 21.0),
                            "amount": tax,
                            "code": f"{tax_code}-{country}",
                            "base": subtotal,
                        }
                    ]
                    if tax > 0
                    else []
                ),
            },
            "lines": (
                [
                    {
                        "desc": final_concept,
                        "qty": 1.0,
                        "unit_price": total,
                        "total": total,
                        "tax_code": tax_code,
                        "tax_amount": tax,
                    }
                ]
                if not extracted_lines
                else [
                    {
                        **line,
                        "tax_code": tax_code,
                        "tax_amount": 0.0,
                    }
                    for line in extracted_lines
                ]
            ),
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
