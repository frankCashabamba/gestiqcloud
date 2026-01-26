"""PDF parser with OCR for tickets, receipts, and general documents."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any


def parse_pdf_ocr(file_path: str) -> dict[str, Any]:
    """Parse PDF file using OCR and extract structured data.

    Detects document type (ticket_pos, invoice, receipt, bank) and extracts
    data accordingly using the appropriate extractor.

    Args:
        file_path: Path to PDF file

    Returns:
        Dict with 'rows' list, detected_type, and metadata
    """
    rows = []
    errors = []
    detected_type = "generic"
    ocr_text = ""

    try:
        from app.modules.imports.services.ocr_service import ocr_service

        if not ocr_service.is_available():
            errors.append("OCR service not available (fitz/tesseract not installed)")
            return _build_error_result(errors)

        # Run OCR (async → sync wrapper)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        ocr_result = loop.run_until_complete(ocr_service.extract_text(file_path))
        ocr_text = ocr_result.text
        layout = ocr_result.layout.value

        # Map layout to doc_type
        layout_to_doctype = {
            "ticket_pos": "ticket_pos",
            "invoice": "invoices",
            "receipt": "expenses",
            "bank_statement": "bank_transactions",
            "table": "generic",
            "form": "generic",
            "unknown": "generic",
        }
        detected_type = layout_to_doctype.get(layout, "generic")

        # Extract data based on layout
        if layout == "ticket_pos":
            from app.modules.imports.extractores.extractor_ticket import extraer_ticket

            resultados = extraer_ticket(ocr_text)
            for canonical in resultados:
                rows.append(_canonical_to_row(canonical, "ticket_pos"))

        elif layout == "invoice":
            from app.modules.imports.extractores.extractor_factura import extraer_factura

            documentos = extraer_factura(ocr_text)
            for doc in documentos:
                rows.append(_documento_to_row(doc, "invoice"))

        elif layout == "receipt":
            from app.modules.imports.extractores.extractor_recibo import extraer_recibo

            documentos = extraer_recibo(ocr_text)
            for doc in documentos:
                rows.append(_documento_to_row(doc, "receipt"))

        elif layout == "bank_statement":
            from app.modules.imports.extractores.extractor_transferencia import (
                extraer_transferencias,
            )

            documentos = extraer_transferencias(ocr_text)
            for doc in documentos:
                rows.append(_documento_to_row(doc, "bank"))

        else:
            # Generic extraction - return OCR text for manual mapping
            rows.append(
                {
                    "doc_type": "generic",
                    "ocr_text": ocr_text[:5000],
                    "text_length": len(ocr_text),
                    "layout_detected": layout,
                    "_metadata": {
                        "parser": "pdf_ocr",
                        "extracted_at": datetime.utcnow().isoformat(),
                    },
                }
            )

    except Exception as e:
        errors.append(f"OCR processing error: {str(e)}")
        return _build_error_result(errors)

    return {
        "rows": rows,
        "headers": _get_headers_for_type(detected_type),
        "detected_type": detected_type,
        "ocr_text_preview": ocr_text[:500] if ocr_text else "",
        "pages_processed": getattr(ocr_result, "pages", 1) if "ocr_result" in dir() else 1,
        "errors": errors,
        "metadata": {
            "parser": "pdf_ocr",
            "layout": layout if "layout" in dir() else "unknown",
            "confidence": getattr(ocr_result, "confidence", 0.5) if "ocr_result" in dir() else 0.5,
        },
    }


def _canonical_to_row(canonical: dict, doc_type: str) -> dict[str, Any]:
    """Convert CanonicalDocument to row format."""
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
            "parser": "pdf_ocr",
            "source": canonical.get("source", "ocr"),
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }


def _documento_to_row(doc: Any, doc_type: str) -> dict[str, Any]:
    """Convert DocumentoProcesado to row format."""
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
            "parser": "pdf_ocr",
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }


def _get_headers_for_type(doc_type: str) -> list[str]:
    """Get expected headers for document type."""
    headers_map = {
        "ticket_pos": ["invoice_number", "issue_date", "total", "lines"],
        "invoices": ["invoice_number", "issue_date", "vendor_name", "total", "tax"],
        "expenses": ["fecha", "importe", "concepto", "categoria"],
        "bank_transactions": ["fecha", "importe", "concepto", "cuenta"],
        "generic": ["ocr_text", "layout_detected"],
    }
    return headers_map.get(doc_type, ["ocr_text"])


def _build_error_result(errors: list[str]) -> dict[str, Any]:
    """Build error result dict."""
    return {
        "rows": [],
        "headers": [],
        "detected_type": "error",
        "errors": errors,
        "metadata": {
            "parser": "pdf_ocr",
            "extracted_at": datetime.utcnow().isoformat(),
        },
    }
