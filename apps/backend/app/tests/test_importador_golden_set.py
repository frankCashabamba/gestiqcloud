from __future__ import annotations

import asyncio
import os
import pathlib
from dataclasses import dataclass

import pytest

from app.modules.importador.doc_type_resolution import promote_doc_type_from_text_fallback
from app.modules.importador.invoice_ocr_rescue import invoice_rescue_from_ocr
from app.modules.importador.ocr_service import extract_text_from_file
from app.modules.importador.text_fallback_extractor import extract_fields_from_text

_IMPORT_DIR = pathlib.Path(__file__).parents[4] / "importacion"


@dataclass(frozen=True)
class GoldenCase:
    filename: str
    expected_doc_type: str
    expected_total: float
    allowed_reason_tags: set[str]
    minimum_confidence: float
    should_use_invoice_rescue: bool = False
    expected_doc_number: str | None = None
    expected_vendor_fragment: str | None = None
    expected_min_line_items: int = 0
    requires_image_opt_in: bool = False


_RESOLUTION_CONFIG = {
    "promotion_blocked_preclass_types": [
        "SALES",
        "PAYROLL",
        "BANK_STATEMENT",
        "BANK",
        "INVENTORY",
        "PRICE_LIST",
        "PRODUCT_LIST",
        "PRODUCTS",
        "COSTING",
        "RECIPE",
    ],
    "restore_stable_preclassified_types": [
        "BANK_MOVEMENTS",
        "BANK_STATEMENT",
        "EXPENSE",
        "EXPENSES",
        "INVOICE",
        "PAYROLL",
        "RECEIPT",
        "SALES",
    ],
    "restore_conflict_doc_types": ["INVOICE", "RECEIPT"],
    "text_fallback_total_field_aliases": ["total_amount", "total_price", "total", "amount"],
    "text_fallback_keyword_confidence": {"INVOICE": 0.68, "RECEIPT": 0.66},
    "text_fallback_like_confidence": {"INVOICE": 0.64, "RECEIPT": 0.61},
    "text_fallback_minimal_confidence": {"RECEIPT": 0.56},
}

_FALLBACK_PATTERNS = {
    "INVOICE": ["factura", "invoice"],
    "RECEIPT": ["recibo", "boleta", "ticket"],
    "PAYROLL": ["payroll", "nomina", "planilla", "lohnabrechnung"],
    "SALES": ["ventas", "summary", "export", "reporte", "report", "sales"],
}

_CANONICAL_FIELDS = {
    "vendor": {"type": "text"},
    "vendor_tax_id": {"type": "text"},
    "doc_number": {"type": "text"},
    "issue_date": {"type": "date"},
    "total_amount": {"type": "numeric"},
    "subtotal": {"type": "numeric"},
    "tax_amount": {"type": "numeric"},
    "payment_method": {"type": "text"},
    "concept": {"type": "text"},
    "line_items": {"type": "list"},
}

_FIELD_ALIASES = {
    "vendor": ["proveedor", "empresa", "razon social"],
    "vendor_tax_id": ["RUC", "NIT", "CIF"],
    "doc_number": ["factura no", "factura no.", "N° factura", "No. factura", "No.", "N°"],
    "issue_date": ["fecha de emision", "fecha emision", "fecha"],
    "total_amount": ["total", "total a pagar", "importe total", "valor total"],
    "subtotal": ["subtotal", "sub total", "base imponible"],
    "tax_amount": ["IVA", "impuesto", "IVA 12%"],
    "payment_method": ["forma de pago", "f. de pago", "metodo de pago"],
    "concept": ["concepto", "detalle", "descripcion"],
}

_AMOUNT_LABELS = {
    "total_amount": ["total", "total a pagar", "valor total"],
    "subtotal": ["subtotal", "sub total"],
    "tax_amount": ["IVA", "IVA 12%"],
}

_GOLDEN_CASES = [
    GoldenCase(
        filename="factura_proveedor_stock_alto_insumos.pdf",
        expected_doc_type="INVOICE",
        expected_total=16567.49,
        allowed_reason_tags={"invoice_keyword", "invoice_like_fields", "invoice_like_line_items"},
        minimum_confidence=0.64,
        should_use_invoice_rescue=True,
        expected_doc_number="FAC-2026-0487",
        expected_vendor_fragment="Distribuidora",
        expected_min_line_items=1,
    ),
    GoldenCase(
        filename="Ventas_2026-02-21_2026-03-23.pdf",
        expected_doc_type="SALES",
        expected_total=169.0,
        allowed_reason_tags={"sales_keyword"},
        minimum_confidence=0.63,
        expected_min_line_items=0,
    ),
    GoldenCase(
        filename="Nómina enero.pdf",
        expected_doc_type="PAYROLL",
        expected_total=2243.04,
        allowed_reason_tags={"payroll_keyword", "payroll_like_fields"},
        minimum_confidence=0.62,
        expected_min_line_items=6,
    ),
    GoldenCase(
        filename="ReciboPDF_037640_003368_638865448560277604.pdf",
        expected_doc_type="RECEIPT",
        expected_total=52.30,
        allowed_reason_tags={"receipt_keyword", "receipt_like_fields"},
        minimum_confidence=0.56,
        expected_min_line_items=0,
    ),
    GoldenCase(
        filename="WhatsApp Image 2026-02-11 at 22.46.23 (1).jpeg",
        expected_doc_type="INVOICE",
        expected_total=2145.00,
        allowed_reason_tags={"invoice_keyword", "invoice_like_fields", "invoice_like_line_items"},
        minimum_confidence=0.64,
        should_use_invoice_rescue=True,
        expected_vendor_fragment="MOLINOS",
        expected_min_line_items=1,
        requires_image_opt_in=True,
    ),
]


def _load_text(filename: str) -> tuple[pathlib.Path, str, list[str] | None]:
    path = _IMPORT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} no disponible")
    ocr = asyncio.run(extract_text_from_file(path.read_bytes(), path.name, bypass_cache=True))
    return path, str(ocr.get("text") or ""), ocr.get("page_texts")


def _extract_fields(text: str, page_texts: list[str] | None) -> dict:
    extracted = extract_fields_from_text(
        text,
        _CANONICAL_FIELDS,
        _FIELD_ALIASES,
        _AMOUNT_LABELS,
        page_texts=page_texts,
    )
    return extracted


@pytest.mark.no_db
@pytest.mark.parametrize("case", _GOLDEN_CASES, ids=lambda c: c.filename)
def test_importador_golden_set_phase1(case: GoldenCase):
    if case.requires_image_opt_in and os.getenv("IMPORTADOR_GOLDEN_INCLUDE_IMAGES") != "1":
        pytest.skip("Imagenes opt-in: defina IMPORTADOR_GOLDEN_INCLUDE_IMAGES=1")

    path, text, page_texts = _load_text(case.filename)
    assert text.strip(), f"{case.filename} no devolvio texto OCR util"

    extracted = _extract_fields(text, page_texts)
    rescued = invoice_rescue_from_ocr(text, existing_fields=extracted) if case.should_use_invoice_rescue else {}
    fields = {**extracted, **rescued}

    promoted_type, promoted_confidence, promoted_reasoning, reason_tag = (
        promote_doc_type_from_text_fallback(
            current_doc_type="OTHER",
            current_confidence=0.35,
            current_reasoning="Native deterministic extraction only.",
            fields=fields,
            content=text,
            filename=path.name,
            resolution_config=_RESOLUTION_CONFIG,
            fallback_patterns=_FALLBACK_PATTERNS,
        )
    )

    assert promoted_type == case.expected_doc_type
    assert promoted_confidence >= case.minimum_confidence
    assert reason_tag in case.allowed_reason_tags
    assert "Promoted" in promoted_reasoning

    total_amount = float(fields.get("total_amount") or 0.0)
    assert abs(total_amount - case.expected_total) < 0.5

    line_items = fields.get("line_items") or []
    assert len(line_items) >= case.expected_min_line_items

    if case.expected_doc_number:
        assert case.expected_doc_number in str(fields.get("doc_number") or "")
    if case.expected_vendor_fragment:
        assert case.expected_vendor_fragment.upper() in str(fields.get("vendor") or "").upper()
