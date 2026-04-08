from __future__ import annotations

import asyncio

import pytest

from app.modules.importador.processing_service import (
    _analysis_indicates_ai_failure,
    _analyze_with_context,
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
