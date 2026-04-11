from __future__ import annotations

import pytest

from app.modules.importador.doc_type_resolution import (
    promote_doc_type_from_text_fallback,
    restore_preclassified_doc_type,
    should_preserve_strong_preclassification,
)
from app.modules.importador.runtime_config import (
    invalidate_runtime_config_cache,
    load_doc_type_patterns,
    load_doc_type_resolution_config,
)


@pytest.mark.no_db
def test_promote_doc_type_from_text_fallback_promotes_receipt_from_minimal_fields():
    invalidate_runtime_config_cache()

    promoted_type, promoted_confidence, promoted_reasoning, reason_tag = (
        promote_doc_type_from_text_fallback(
            current_doc_type="OTHER",
            current_confidence=0.2,
            current_reasoning="fallback",
            fields={
                "issue_date": "2026-01-16",
                "total_amount": 2145,
                "vendor_tax_id": "1890004195001",
            },
            content="texto OCR sin clasificacion usable",
            filename="whatsapp-image.jpeg",
            resolution_config=load_doc_type_resolution_config(None),
            fallback_patterns=load_doc_type_patterns(None),
        )
    )

    assert promoted_type == "RECEIPT"
    assert promoted_confidence >= 0.61
    assert reason_tag == "receipt_like_fields"
    assert "Promoted from OCR text fallback" in promoted_reasoning


@pytest.mark.no_db
def test_promote_doc_type_from_text_fallback_promotes_invoice_when_doc_number_or_lines_exist():
    invalidate_runtime_config_cache()

    promoted_type, promoted_confidence, _, reason_tag = promote_doc_type_from_text_fallback(
        current_doc_type="OTHER",
        current_confidence=0.2,
        current_reasoning="fallback",
        fields={
            "issue_date": "2026-01-16",
            "total_amount": 2145,
            "vendor_tax_id": "1890004195001",
            "doc_number": "001-002-000123",
            "line_items": [{"description": "Harina", "quantity": 2}],
        },
        content="texto OCR sin clasificacion usable",
        filename="factura.jpeg",
        resolution_config=load_doc_type_resolution_config(None),
        fallback_patterns=load_doc_type_patterns(None),
    )

    assert promoted_type == "INVOICE"
    assert promoted_confidence >= 0.64
    assert reason_tag in {"invoice_keyword", "invoice_like_fields"}


@pytest.mark.no_db
def test_promote_doc_type_from_text_fallback_respects_sales_preclassification():
    invalidate_runtime_config_cache()

    promoted_type, promoted_confidence, promoted_reasoning, reason_tag = (
        promote_doc_type_from_text_fallback(
            current_doc_type="OTHER",
            current_confidence=0.2,
            current_reasoning="fallback",
            fields={
                "total_amount": 79.24,
                "line_items": [{"description": "Pedido 1"}, {"description": "Pedido 2"}],
            },
            content="Ventas del dia total 79.24",
            filename="Ventas_2026-02-21_2026-03-23.pdf",
            pre_class_doc_type="SALES",
            resolution_config=load_doc_type_resolution_config(None),
            fallback_patterns=load_doc_type_patterns(None),
        )
    )

    assert promoted_type == "OTHER"
    assert promoted_confidence == 0.2
    assert promoted_reasoning == "fallback"
    assert reason_tag is None


@pytest.mark.no_db
def test_restore_preclassified_doc_type_recovers_sales_from_other_result():
    invalidate_runtime_config_cache()

    restored_type, restored_confidence, restored_reasoning, reason_tag = (
        restore_preclassified_doc_type(
            current_doc_type="OTHER",
            current_confidence=0.2,
            current_reasoning="fallback",
            pre_class_doc_type="SALES",
            pre_class_confidence=0.7,
            pre_class_layer="filename_pattern",
            resolution_config=load_doc_type_resolution_config(None),
        )
    )

    assert restored_type == "SALES"
    assert restored_confidence == 0.7
    assert reason_tag == "preclassification_restore"
    assert "filename_pattern" in restored_reasoning


@pytest.mark.no_db
def test_restore_preclassified_doc_type_prefers_receipt_over_conflicting_invoice_fallback():
    invalidate_runtime_config_cache()

    restored_type, restored_confidence, restored_reasoning, reason_tag = (
        restore_preclassified_doc_type(
            current_doc_type="INVOICE",
            current_confidence=0.68,
            current_reasoning="fallback",
            pre_class_doc_type="RECEIPT",
            pre_class_confidence=0.75,
            pre_class_layer="filename_pattern",
            resolution_config=load_doc_type_resolution_config(None),
        )
    )

    assert restored_type == "RECEIPT"
    assert restored_confidence == 0.75
    assert reason_tag == "preclassification_restore"
    assert "RECEIPT" in restored_reasoning


@pytest.mark.no_db
def test_should_preserve_strong_preclassification_blocks_inventory_override():
    assert should_preserve_strong_preclassification(
        pre_class_doc_type="EXPENSES",
        pre_class_confidence=0.7,
        product_like_doc_types={"INVENTORY", "PRICE_LIST", "PRODUCT_LIST", "PRODUCTS"},
        min_confidence=0.65,
    )
