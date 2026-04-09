from __future__ import annotations

import asyncio

import pytest

from app.modules.importador.processing_service import (
    _analysis_indicates_ai_failure,
    _analyze_with_context,
    _build_table_prompt_preview,
)
from app.modules.importador.text_fallback_extractor import (
    extract_line_items_table_preview_from_text,
)


@pytest.mark.no_db
def test_analyze_with_context_uses_processing_runtime_threshold(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_analyze_document_fn(content, filename, format_hint, **kwargs):
        captured["content"] = content
        captured["filename"] = filename
        captured["format_hint"] = format_hint
        captured["image_bytes"] = kwargs.get("image_bytes")
        return {"doc_type": "OTHER", "confidence": 0.0, "reasoning": "ok", "fields": {}}

    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_processing_runtime_config",
        lambda _db=None: {
            "ocr_text_sufficient_min_chars": 20,
            "llm_text_preview_chars": 6000,
            "structured_preview_rows": 5,
            "structured_preview_fields": 8,
            "doc_type_hint_min_confidence": 0.65,
            "structured_output_rows_limit": 200,
            "persist_text_ocr_max_chars": 50000,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_ai_runtime_config",
        lambda _db=None: {
            "ocr_min_quality": 0.1,
            "openai_fallback_ocr_quality_threshold": 0.1,
            "ocr_length_target_chars": 1200,
            "ocr_word_target": 180,
            "ocr_alpha_ratio_target": 0.6,
            "ocr_noise_ratio_limit": 0.2,
            "ocr_score_weight_length": 0.35,
            "ocr_score_weight_words": 0.35,
            "ocr_score_weight_alpha": 0.2,
            "ocr_score_weight_clean": 0.1,
        },
    )

    asyncio.run(
        _analyze_with_context(
            analyze_document_fn=fake_analyze_document_fn,
            content="texto OCR suficiente para evitar vision",
            filename="doc.pdf",
            format_hint="PDF_OCR",
            has_structured_rows=False,
            recipe_config=None,
            vision_image_bytes=b"fake-image",
            fallback_patterns={},
            canonical_fields={},
            prompt_config={},
            db=None,
        )
    )

    assert captured["image_bytes"] is None


@pytest.mark.no_db
def test_analyze_with_context_rejects_low_quality_image_ocr(monkeypatch):
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "OTHER", "confidence": 0.0, "reasoning": "ok", "fields": {}}

    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_processing_runtime_config",
        lambda _db=None: {
            "ocr_text_sufficient_min_chars": 20,
            "llm_text_preview_chars": 6000,
            "structured_preview_rows": 5,
            "structured_preview_fields": 8,
            "doc_type_hint_min_confidence": 0.65,
            "structured_output_rows_limit": 200,
            "persist_text_ocr_max_chars": 50000,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_ai_runtime_config",
        lambda _db=None: {
            "ocr_min_quality": 0.9,
            "openai_fallback_ocr_quality_threshold": 0.9,
            "ocr_length_target_chars": 1200,
            "ocr_word_target": 180,
            "ocr_alpha_ratio_target": 0.6,
            "ocr_noise_ratio_limit": 0.2,
            "ocr_score_weight_length": 0.35,
            "ocr_score_weight_words": 0.35,
            "ocr_score_weight_alpha": 0.2,
            "ocr_score_weight_clean": 0.1,
        },
    )

    with pytest.raises(ValueError, match="Imagen de mala calidad"):
        asyncio.run(
            _analyze_with_context(
                analyze_document_fn=fake_analyze_document_fn,
                content="A B C D E 12345 !!! A B C D E 12345 !!!",
                filename="foto.jpg",
                format_hint="IMAGE_OCR",
                has_structured_rows=False,
                recipe_config=None,
                vision_image_bytes=b"fake-image",
                fallback_patterns={},
                canonical_fields={},
                prompt_config={},
                db=None,
            )
        )

    assert called["count"] == 0


@pytest.mark.no_db
def test_analysis_indicates_ai_failure_uses_runtime_tokens(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_processing_runtime_config",
        lambda _db=None: {
            "ocr_text_sufficient_min_chars": 100,
            "llm_text_preview_chars": 6000,
            "structured_preview_rows": 5,
            "structured_preview_fields": 8,
            "doc_type_hint_min_confidence": 0.65,
            "structured_output_rows_limit": 200,
            "persist_text_ocr_max_chars": 50000,
            "ai_failure_tokens": ["gateway exploded"],
            "table_only_doc_types": [],
            "product_like_doc_types": [],
            "recipe_name_field_candidates": [],
        },
    )

    assert _analysis_indicates_ai_failure(
        {"raw_response": "Gateway exploded while contacting provider"}
    )


@pytest.mark.no_db
def test_table_preview_preserves_header_order():
    text = """
Item
Codigo
Descripcion
Unidad
Cantidad
P. Unitario
Importe
1
PRO-0050
Aceite
ml
60,000 ml
$ 0.0034
$ 204.00
""".strip()

    field_aliases = {
        "description": ["item"],
        "supplier_ref": ["codigo"],
        "concept": ["descripcion"],
        "quantity": ["cantidad"],
        "unit_price": ["p. unitario"],
        "total_price": ["importe"],
    }

    preview = extract_line_items_table_preview_from_text(text, field_aliases)
    prompt = _build_table_prompt_preview(preview, max_rows=3)

    assert preview["headers"] == [
        "item",
        "codigo",
        "descripcion",
        "unidad",
        "cantidad",
        "p. unitario",
        "importe",
    ]
    assert (
        "Headers: item | codigo | descripcion | unidad | cantidad | p. unitario | importe" in prompt
    )
    assert "1 | PRO-0050 | Aceite | ml | 60,000 ml | $ 0.0034 | $ 204.00" in prompt


@pytest.mark.no_db
def test_table_preview_groups_line_items_by_page():
    page_1 = """
Item
Codigo
Descripcion
Unidad
Cantidad
P. Unitario
Importe
14
PRO-0040
Cocoa Amarga
g
45,000 g
$ 0.0059
$ 265.50
""".strip()
    page_2 = """
Item
Codigo
Descripcion
Unidad
Cantidad
P. Unitario
Importe
15
PRO-0060
Crema Chantilly
g
35,000 g
$ 0.0042
$ 147.00
""".strip()

    field_aliases = {
        "supplier_ref": ["codigo"],
        "description": ["descripcion"],
        "unit": ["unidad"],
        "quantity": ["cantidad"],
        "unit_price": ["p. unitario"],
        "total_price": ["importe"],
    }

    preview = extract_line_items_table_preview_from_text(
        f"{page_1}\n\n{page_2}",
        field_aliases,
        page_texts=[page_1, page_2],
    )

    assert preview["headers"] == [
        "item",
        "codigo",
        "descripcion",
        "unidad",
        "cantidad",
        "p. unitario",
        "importe",
    ]
    assert len(preview["line_item_page_groups"]) == 2
    assert preview["line_item_page_groups"][0]["source_page"] == 1
    assert preview["line_item_page_groups"][1]["source_page"] == 2
    assert preview["line_item_page_groups"][0]["line_items"][0]["supplier_ref"] == "PRO-0040"
    assert preview["line_item_page_groups"][1]["line_items"][0]["supplier_ref"] == "PRO-0060"
    assert len(preview["line_items"]) == 2
