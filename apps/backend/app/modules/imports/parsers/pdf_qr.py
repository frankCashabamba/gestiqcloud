"""PDF parser with QR code extraction for invoices and receipts."""

from datetime import datetime
from typing import Any


def parse_pdf_qr(file_path: str) -> dict[str, Any]:
    """Parse PDF file with QR code extraction.

    Uses pyzbar to extract QR codes from PDF pages and attempts to parse
    invoice/receipt data from them. Falls back to OCR if available.

    Args:
        file_path: Path to PDF file

    Returns:
        Dict with 'documents' list and metadata
    """
    documents = []
    pages_processed = 0
    qr_codes_found = 0
    errors = []

    try:
        # Check if required libraries are available
        try:
            import pdf2image
            import pyzbar.pyzbar as pyzbar
        except ImportError as e:
            errors.append(
                f"Missing required library: {e}. " "Install with: pip install pdf2image pyzbar"
            )
            return {
                "documents": [],
                "pages_processed": 0,
                "qr_codes_found": 0,
                "errors": errors,
                "source_type": "pdf",
                "parser": "pdf_qr",
            }

        # Convert PDF to images
        images = pdf2image.convert_from_path(file_path)
        pages_processed = len(images)

        for page_idx, image in enumerate(images, start=1):
            try:
                # Extract QR codes from page
                qr_results = pyzbar.decode(image)

                if qr_results:
                    for qr in qr_results:
                        qr_codes_found += 1
                        qr_data = qr.data.decode("utf-8", errors="ignore")

                        # Try to parse QR data (common formats: RUC|Razón|..., space-separated, etc.)
                        doc = _parse_qr_data(qr_data, page_idx, qr_codes_found)
                        if doc:
                            documents.append(doc)

            except Exception as e:
                errors.append(f"Error processing page {page_idx}: {str(e)}")

    except Exception as e:
        errors.append(f"Error reading PDF: {str(e)}")

    return {
        "documents": documents,
        "pages_processed": pages_processed,
        "qr_codes_found": qr_codes_found,
        "rows_parsed": len(documents),
        "errors": errors,
        "source_type": "pdf",
        "parser": "pdf_qr",
    }


def _parse_qr_data(qr_data: str, page: int, qr_index: int) -> dict[str, Any] | None:
    """Parse QR code data string to extract invoice/document info.

    Supports common formats:
    - CFDI/Mexico: "RUC|Razón|RFC|..."
    - UBL/Ecuador: Space or pipe-separated fields
    - Generic: Key=value pairs or pipe-separated values

    Args:
        qr_data: Decoded QR code string
        page: Page number where QR was found
        qr_index: QR code index

    Returns:
        Dict with parsed document data or None
    """
    if not qr_data or not qr_data.strip():
        return None

    doc = {
        "doc_type": "invoice",  # Assume invoice unless detected otherwise
        "qr_data": qr_data,
        "source": "pdf_qr",
        "_metadata": {
            "parser": "pdf_qr",
            "page": page,
            "qr_index": qr_index,
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }

    # Try pipe-separated format (common in Ecuador/Latin America)
    if "|" in qr_data:
        parts = [p.strip() for p in qr_data.split("|")]

        # Common pattern: RUC|BusinessName|Invoice#|Date|Amount|...
        if len(parts) >= 5:
            doc.update(
                {
                    "vendor": {
                        "tax_id": parts[0],
                        "name": parts[1] if len(parts) > 1 else None,
                    },
                    "invoice_number": parts[2] if len(parts) > 2 else None,
                    "issue_date": parts[3] if len(parts) > 3 else None,
                    "totals": {
                        "total": _to_float(parts[4]) if len(parts) > 4 else None,
                    },
                }
            )

    # Try key=value format
    elif "=" in qr_data:
        pairs = qr_data.split("&") if "&" in qr_data else qr_data.split(",")
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.strip().lower()
                value = value.strip()

                # Map known keys
                if key in ["ruc", "tax_id", "nit", "cif"]:
                    if "vendor" not in doc:
                        doc["vendor"] = {}
                    doc["vendor"]["tax_id"] = value
                elif key in ["name", "razon", "razón", "business_name"]:
                    if "vendor" not in doc:
                        doc["vendor"] = {}
                    doc["vendor"]["name"] = value
                elif key in ["invoice", "invoicenumber", "numero", "numero_factura"]:
                    doc["invoice_number"] = value
                elif key in ["date", "fecha", "issue_date", "fecha_emision"]:
                    doc["issue_date"] = value
                elif key in ["total", "amount", "monto", "total_amount"]:
                    doc["totals"] = {"total": _to_float(value)}
                elif key in ["currency", "moneda"]:
                    doc["currency"] = value

    # Space-separated values (fallback)
    else:
        parts = qr_data.split()
        if len(parts) >= 2:
            doc["vendor"] = {
                "tax_id": parts[0] if parts[0].isalnum() or "-" in parts[0] else None,
                "name": " ".join(parts[1:]) if len(parts) > 1 else None,
            }

    # Clean nulls
    doc = _clean_dict(doc)

    # Return None if no meaningful data extracted
    if len(doc) <= 3:  # Only doc_type, source, _metadata
        return None

    return doc


def _to_float(val: str) -> float | None:
    """Convert string to float."""
    if not val:
        return None
    try:
        return float(val.replace(",", ".").strip())
    except (ValueError, TypeError):
        return None


def _clean_dict(d: dict) -> dict:
    """Remove keys with None or empty string values."""
    if not isinstance(d, dict):
        return d
    return {
        k: _clean_dict(v) if isinstance(v, dict) else v
        for k, v in d.items()
        if v is not None and v != "" and (not isinstance(v, dict) or any(_clean_dict(v).values()))
    }
