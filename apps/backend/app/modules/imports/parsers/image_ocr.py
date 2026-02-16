"""Image parser with OCR for tickets, receipts, and general documents."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from app.modules.imports.application.photo_utils import ocr_texto
from app.modules.imports.extractores.utilidades import detect_document_type


def parse_image_ocr(file_path: str) -> dict[str, Any]:
    """Parse an image using OCR and extract structured data."""
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    try:
        p = Path(file_path)
        content = p.read_bytes()
        text = ocr_texto(content, filename=p.name)
        doc_type = detect_document_type(text or "")

        if doc_type == "pos_ticket":
            from app.modules.imports.extractores.extractor_ticket import extraer_ticket

            for canonical in extraer_ticket(text):
                rows.append(_canonical_to_row(canonical, "ticket_pos"))
            detected_type = "ticket_pos"

        elif doc_type == "invoice":
            from app.modules.imports.extractores.extractor_factura import extract_invoice

            for doc in extract_invoice(text):
                rows.append(_documento_to_row(doc, "invoice"))
            detected_type = "invoices"

        elif doc_type == "receipt":
            from app.modules.imports.extractores.extractor_recibo import extract_receipt

            for doc in extract_receipt(text):
                rows.append(_documento_to_row(doc, "receipt"))
            detected_type = "expenses"

        elif doc_type == "transfer":
            from app.modules.imports.extractores.extractor_transferencia import extract_transfers

            for doc in extract_transfers(text):
                rows.append(_documento_to_row(doc, "bank"))
            detected_type = "bank_transactions"

        else:
            detected_type = "generic"
            rows.append(
                {
                    "doc_type": "generic",
                    "ocr_text": (text or "")[:5000],
                    "text_length": len(text or ""),
                    "layout_detected": doc_type,
                    "_metadata": {
                        "parser": "image_ocr",
                        "extracted_at": datetime.utcnow().isoformat(),
                    },
                }
            )

        return {
            "rows": rows,
            "headers": _get_headers_for_type(detected_type),
            "detected_type": detected_type,
            "ocr_text_preview": (text or "")[:500],
            "pages_processed": 1,
            "errors": errors,
            "metadata": {
                "parser": "image_ocr",
                "layout": doc_type,
                "confidence": 0.7,
            },
        }

    except Exception as e:
        errors.append(f"OCR processing error: {str(e)}")
        return _build_error_result(errors)


def _canonical_to_row(canonical: dict, doc_type: str) -> dict[str, Any]:
    totals = canonical.get("totals", {})
    vendor = canonical.get("vendor", {})

    return {
        "doc_type": doc_type,
        "invoice_number": canonical.get("invoice_number"),
        "issue_date": canonical.get("issue_date"),
        "vendor_name": vendor.get("name") if isinstance(vendor, dict) else None,
        "vendor_tax_id": vendor.get("tax_id") if isinstance(vendor, dict) else None,
        "subtotal": totals.get("subtotal"),
        "tax": totals.get("tax"),
        "total": totals.get("total"),
        "currency": canonical.get("currency", "USD"),
        "lines": canonical.get("lines", []),
        "confidence": canonical.get("confidence", 0.5),
        "_metadata": {
            "parser": "image_ocr",
            "source": canonical.get("source", "ocr"),
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }


def _documento_to_row(doc: Any, doc_type: str) -> dict[str, Any]:
    if hasattr(doc, "model_dump"):
        data = doc.model_dump()
    elif isinstance(doc, dict):
        data = doc
    else:
        data = {"value": str(doc)}

    return {
        "doc_type": doc_type,
        "importe": data.get("importe"),
        "fecha": data.get("fecha"),
        "concepto": data.get("concepto"),
        "cliente": data.get("cliente"),
        "categoria": data.get("categoria"),
        "invoice": data.get("invoice"),
        "cuenta": data.get("cuenta"),
        "origen": data.get("origen", "ocr"),
        "_metadata": {
            "parser": "image_ocr",
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }


def _get_headers_for_type(doc_type: str) -> list[str]:
    headers_map = {
        "ticket_pos": ["invoice_number", "issue_date", "total", "lines"],
        "invoices": ["invoice_number", "issue_date", "vendor_name", "total", "tax"],
        "expenses": ["fecha", "importe", "concepto", "categoria"],
        "bank_transactions": ["fecha", "importe", "concepto", "cuenta"],
        "generic": ["ocr_text", "layout_detected"],
    }
    return headers_map.get(doc_type, ["ocr_text"])


def _build_error_result(errors: list[str]) -> dict[str, Any]:
    return {
        "rows": [],
        "headers": [],
        "detected_type": "error",
        "errors": errors,
        "metadata": {
            "parser": "image_ocr",
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }
