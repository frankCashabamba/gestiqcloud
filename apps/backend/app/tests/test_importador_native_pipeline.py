from __future__ import annotations

import asyncio

from app.modules.importador import native_analyzer
from app.modules.importador.ocr_quality import estimate_text_quality


def test_native_analyzer_merges_pre_extracted_fields_and_derives_total(monkeypatch):
    def fake_extract_fields_from_text(*args, **kwargs):
        del args, kwargs
        return {
            "issue_date": "2026-04-14",
            "vendor": "Proveedor Demo",
            "line_items": [{"description": "Harina", "total": "2145.00"}],
        }

    def fake_detect_document_total(fields, aliases=None):
        del aliases
        if fields.get("line_items"):
            return 2145.0
        return None

    monkeypatch.setattr(native_analyzer, "extract_fields_from_text", fake_extract_fields_from_text)
    monkeypatch.setattr(native_analyzer, "detect_document_total", fake_detect_document_total)

    result = asyncio.run(
        native_analyzer.analyze_document(
            "texto ocr base",
            "WhatsApp Image 2026-02-11 at 22.46.23 (1).jpeg",
            "IMAGE_OCR",
            pre_extracted_fields={"customer": "Maria Aurora", "concept": "Factura proveedor"},
        )
    )

    fields = result["fields"]
    assert result["doc_type"] == "OTHER"
    assert result["model_used"] == "native-deterministic"
    assert result["analysis_path"] == "ok_native"
    assert fields["customer"] == "Maria Aurora"
    assert fields["concept"] == "Factura proveedor"
    assert fields["vendor"] == "Proveedor Demo"
    assert fields["issue_date"] == "2026-04-14"
    assert fields["total_amount"] == 2145.0
    assert result["confidence"] >= 0.6
    assert result["requires_review"] is False


def test_estimate_text_quality_rewards_clean_dense_text():
    runtime = {
        "ocr_length_target_chars": 60,
        "ocr_word_target": 8,
        "ocr_alpha_ratio_target": 0.5,
        "ocr_noise_ratio_limit": 0.1,
        "ocr_score_weight_length": 0.35,
        "ocr_score_weight_words": 0.35,
        "ocr_score_weight_alpha": 0.2,
        "ocr_score_weight_clean": 0.1,
    }

    clean = estimate_text_quality(
        "Factura 001 Proveedor Demo Total 2145.00 Fecha 2026-04-14",
        ocr_runtime=runtime,
    )
    noisy = estimate_text_quality(
        "x 1 ! @@@ 2145 ???",
        ocr_runtime=runtime,
    )

    assert clean["score"] > noisy["score"]
    assert 0.0 <= noisy["score"] <= clean["score"] <= 1.0
    assert clean["words"] > noisy["words"]
