from __future__ import annotations

import asyncio

import pytest

from app.modules.importador.ai_classifier import (
    _amount_has_monetary_context,
    _extract_labeled_amount,
    _extract_vendor_name_from_ocr,
)
from app.modules.importador.invoice_ocr_rescue import invoice_rescue_from_ocr
from app.modules.importador.processing_service import (
    _STRUCTURED_SKIP_FORMATS,
    _XML_HEADER_TO_CANONICAL,
    _XML_INVOICE_FORMATS,
    _XML_TIPO_DOCUMENTO_MAP,
    RecipeContext,
    _analysis_requires_review_from_field_confidences,
    _analysis_indicates_ai_failure,
    _analyze_with_context,
    _build_ai_attempt_fingerprint,
    _build_table_prompt_preview,
    _looks_like_noisy_scalar_text,
    _merge_text_fallback_fields,
    _pre_extract_route_decision,
    _prefer_text_candidate_over_existing,
    _repair_pre_extracted_fields,
    _sanitize_text_fallback_fields,
    _should_skip_useless_retry,
    decide_processing_lane,
    process_import_document,
)
from app.modules.importador.text_fallback_extractor import (
    _infer_total_amount_from_lines,
    extract_fields_from_text,
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
            reprocess_mode="deep",
        )
    )

    # En modo deep siempre se pasa la imagen a la IA para análisis visual completo
    assert captured["image_bytes"] is not None


@pytest.mark.no_db
def test_pre_extract_route_decision_uses_configured_threshold():
    pre_fields = {
        "total_amount": 100.0,
        "vendor": "ACME S.A.",
        "doc_number": "F-001",
    }

    relaxed = _pre_extract_route_decision(
        pre_fields=pre_fields,
        processing_cfg={
            "pre_extract_min_strong_fields": 3,
            "pre_extract_min_confidence": 0.62,
        },
    )
    strict = _pre_extract_route_decision(
        pre_fields=pre_fields,
        processing_cfg={
            "pre_extract_min_strong_fields": 4,
            "pre_extract_min_confidence": 0.62,
        },
    )

    assert relaxed["skip_ai"] is True
    assert relaxed["strong_count"] == 3
    assert strict["skip_ai"] is False
    assert strict["confidence"] == relaxed["confidence"]


@pytest.mark.no_db
def test_pre_extract_route_decision_does_not_count_missing_total_as_strong_field():
    decision = _pre_extract_route_decision(
        pre_fields={"concept": "NOTA DE VENTA RE"},
        processing_cfg={
            "pre_extract_min_strong_fields": 3,
            "pre_extract_min_confidence": 0.62,
        },
    )

    assert decision["has_total"] is False
    assert decision["strong_count"] == 0
    assert decision["skip_ai"] is False


@pytest.mark.no_db
def test_analysis_requires_review_from_field_confidences_detects_weak_critical_fields():
    analysis = {
        "field_confidences": {
            "vendor": {"value": "ACME", "confidence": 0.62},
            "total_amount": {"value": 123.45, "confidence": 0.94},
        }
    }

    assert _analysis_requires_review_from_field_confidences(analysis) is True
    assert _analysis_requires_review_from_field_confidences(
        {
            "field_confidences": {
                "vendor": {"value": "ACME", "confidence": 0.82},
                "total_amount": {"value": 123.45, "confidence": 0.94},
            }
        }
    ) is False


@pytest.mark.no_db
def test_analyze_with_context_calls_ai_in_fast_mode_when_text_is_sufficient(monkeypatch):
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "INVOICE", "confidence": 0.9, "reasoning": "unexpected", "fields": {}}

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

    analysis = asyncio.run(
        _analyze_with_context(
            analyze_document_fn=fake_analyze_document_fn,
            content="texto OCR muy suficiente para saltar IA pesada en fast mode",
            filename="doc.pdf",
            format_hint="PDF_OCR",
            has_structured_rows=False,
            recipe_config=None,
            vision_image_bytes=None,
            fallback_patterns={},
            canonical_fields={},
            prompt_config={},
            db=None,
            reprocess_mode="fast",
        )
    )

    assert called["count"] == 1
    assert analysis["doc_type"] == "INVOICE"
    assert analysis["confidence"] == 0.9


@pytest.mark.no_db
def test_decide_processing_lane_routes_sufficient_images_text_first():
    decision = decide_processing_lane(
        doc_format="IMAGE_OCR",
        has_structured=False,
        has_vision=True,
        text_is_sufficient=True,
        has_semantic_hint=False,
        has_cached_analysis=False,
        is_first_import=True,
        previous_confidence=None,
        deep_reprocess=False,
        processing_cfg={
            "lane_timeout_fast": 12.0,
            "lane_timeout_deep": 90.0,
            "ocr_quality_vision_threshold": 0.45,
        },
        ocr_quality_score=0.80,
    )

    assert decision.lane == "deep"
    assert decision.timeout_secs == 45.0
    assert decision.force_vision is False
    assert decision.vision_first is False
    assert "text_first" in decision.reasons


@pytest.mark.no_db
def test_analyze_with_context_image_pre_extract_can_skip_ai(monkeypatch):
    """Si el pre-extract ya cubre suficiente señal, la IA no debe ejecutarse en imágenes."""
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {
            "doc_type": "INVOICE",
            "confidence": 0.82,
            "reasoning": "ai",
            "fields": {"total_amount": 10},
        }

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
        "app.modules.importador.processing_service.invoice_rescue_from_ocr",
        lambda text, existing_fields=None: {
            "vendor": "ACME S.A.",
            "issue_date": "2026-04-18",
            "total_amount": 42.0,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.extract_fields_from_text",
        lambda **_kwargs: {
            "vendor": "ACME S.A.",
            "issue_date": "2026-04-18",
            "total_amount": 42.0,
            "doc_number": "F-001",
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service._pre_extract_route_decision",
        lambda **_kwargs: {
            "skip_ai": True,
            "confidence": 0.91,
            "strong_count": 3,
            "min_strong_fields": 3,
            "min_confidence": 0.62,
            "has_total": True,
            "has_date": True,
            "has_doc": True,
            "has_vendor": True,
            "has_tax_id": False,
        },
    )

    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.update_documento",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.add_log",
        lambda *args, **kwargs: None,
    )

    async def fake_extract_text_fn(file_bytes, filename, bypass_cache=False):
        del file_bytes, filename, bypass_cache
        return {
            "text": "texto OCR suficientemente largo y limpio para resolver el documento",
            "format": "IMAGE_OCR",
            "vision_image_bytes": b"fake-image",
            "ocr_quality_score": 0.8,
        }

    result = asyncio.run(
        process_import_document(
            db=None,
            doc=type("Doc", (), {"id": 1})(),
            tenant_id=None,
            user_id=None,
            file_bytes=b"fake-image",
            filename="doc.jpg",
            tipo_archivo="IMAGE_OCR",
            force=False,
            extract_text_fn=fake_extract_text_fn,
            analyze_document_fn=fake_analyze_document_fn,
            recipe_context=RecipeContext(explicit_recipe_context=True),
        )
    )

    assert called["count"] == 0
    assert result.raw_ai_json["analysis"]["raw_response"] == "reason=pre_extract_skip_ai"
    assert result.datos_extraidos["total_amount"] == 42.0


@pytest.mark.no_db
def test_pre_extract_skip_ai_applies_ocr_repairs_before_persist(monkeypatch):
    called = {"count": 0}
    updates: list[dict[str, object]] = []

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "OTHER", "confidence": 0.0, "reasoning": "unexpected", "fields": {}}

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
            "pre_extract_min_strong_fields": 3,
            "pre_extract_min_confidence": 0.62,
            "ocr_quality_vision_threshold": 0.45,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.invoice_rescue_from_ocr",
        lambda text, existing_fields=None: {
            "vendor": "tribuy Special Resolucién 04519 sg or ie",
            "doc_number": "001-001-000120085",
            "subtotal": 1145.0,
            "tax_amount": 1145.0,
            "total_amount": 2145.0,
            "line_items": [
                {
                    "description": "IHARINA TRADICION PREMIUM 50 KG F/",
                    "quantity": 50.0,
                    "unit_price": 42.9,
                    "total_price": 2145.0,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.extract_fields_from_text",
        lambda **_kwargs: {
            "concept": "Hul - w._. U",
            "payment_method": "Credito",
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.update_documento",
        lambda _db, _doc, payload: updates.append(payload),
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.add_log",
        lambda *args, **kwargs: None,
    )

    ocr_text = """
    FACTURA : 001-001-000120085
    FECHA Y HORA AUTORIZACION : 2026-01-16T08:56:16-05:00
    RUC :1890004195001
    Fecha de Emisión : viernes, 16 de enero de 2026
    T-HARINA-00006 0788115386881 50.00 IHARINA TRADICION PREMIUM 50 KG F/ 42.90 2,145.00
    VALOR TOTAL 2,145.00
    """.strip()

    async def fake_extract_text_fn(file_bytes, filename, bypass_cache=False):
        del file_bytes, filename, bypass_cache
        return {
            "text": ocr_text,
            "format": "IMAGE_OCR",
            "vision_image_bytes": b"fake-image",
            "ocr_quality_score": 0.98,
        }

    result = asyncio.run(
        process_import_document(
            db=None,
            doc=type("Doc", (), {"id": 1, "tenant_id": None})(),
            tenant_id=None,
            user_id=None,
            file_bytes=b"fake-image",
            filename="doc.jpg",
            tipo_archivo="IMAGE_OCR",
            force=False,
            extract_text_fn=fake_extract_text_fn,
            analyze_document_fn=fake_analyze_document_fn,
            recipe_context=RecipeContext(explicit_recipe_context=True),
        )
    )

    assert called["count"] == 0
    assert result.raw_ai_json["analysis"]["raw_response"] == "reason=pre_extract_skip_ai"
    assert "vendor" not in result.datos_extraidos
    assert result.datos_extraidos["concept"] == "HARINA TRADICION PREMIUM 50 KG F/"
    assert result.datos_extraidos["issue_date"] == "2026-01-16"
    assert result.datos_extraidos["vendor_tax_id"] == "1890004195001"
    assert len(result.datos_extraidos["line_items"]) == 1
    assert (
        result.datos_extraidos["line_items"][0]["description"]
        == "HARINA TRADICION PREMIUM 50 KG F/"
    )
    assert any(
        payload.get("error_detalle") is None for payload in updates if isinstance(payload, dict)
    )


@pytest.mark.no_db
def test_low_evidence_visual_doc_skips_ai_and_marks_review_message(monkeypatch):
    called = {"count": 0}
    updates: list[dict[str, object]] = []

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "OTHER", "confidence": 0.0, "reasoning": "unexpected", "fields": {}}

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
            "pre_extract_min_strong_fields": 3,
            "pre_extract_min_confidence": 0.62,
            "ocr_quality_vision_threshold": 0.45,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.invoice_rescue_from_ocr",
        lambda text, existing_fields=None: {},
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.extract_fields_from_text",
        lambda **_kwargs: {"concept": "NOTA DE VENTA RE"},
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.update_documento",
        lambda _db, _doc, payload: updates.append(payload),
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.add_log",
        lambda *args, **kwargs: None,
    )

    async def fake_extract_text_fn(file_bytes, filename, bypass_cache=False):
        del file_bytes, filename, bypass_cache
        return {
            "text": "NOTA DE VENTA RE\nDIRECCION\nCIUDAD\nR.U.C\nTELEFONO\nF. DE PAGO\nCANT.\nDESCRIPCION\nVUNIT\nVTOTAL\n",
            "format": "IMAGE_OCR",
            "vision_image_bytes": b"fake-image",
            "ocr_quality_score": 0.42,
        }

    result = asyncio.run(
        process_import_document(
            db=None,
            doc=type("Doc", (), {"id": 1, "tenant_id": None})(),
            tenant_id=None,
            user_id=None,
            file_bytes=b"fake-image",
            filename="doc.jpg",
            tipo_archivo="IMAGE_OCR",
            force=False,
            extract_text_fn=fake_extract_text_fn,
            analyze_document_fn=fake_analyze_document_fn,
            recipe_context=RecipeContext(explicit_recipe_context=True),
        )
    )

    assert called["count"] == 0
    assert result.raw_ai_json["analysis"]["raw_response"] == "reason=low_evidence_visual_review"
    assert result.tipo_documento_detectado == "OTHER"
    assert any(
        isinstance(payload.get("error_detalle"), str)
        and "foto mas nitida" in str(payload.get("error_detalle"))
        for payload in updates
        if isinstance(payload, dict)
    )


@pytest.mark.no_db
def test_low_evidence_visual_doc_skips_ai_when_only_secondary_fields_exist(monkeypatch):
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "OTHER", "confidence": 0.0, "reasoning": "unexpected", "fields": {}}

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
            "pre_extract_min_strong_fields": 3,
            "pre_extract_min_confidence": 0.62,
            "ocr_quality_vision_threshold": 0.45,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.invoice_rescue_from_ocr",
        lambda text, existing_fields=None: {},
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.extract_fields_from_text",
        lambda **_kwargs: {
            "vendor": "ARCAMPO LOSHMANZANOS",
            "doc_number": "00230",
            "payment_method": "Tarjeta",
            "concept": "icafix*frfi~ufi 5,34",
            "total_amount": 10.0,
            "tax_amount": 23.0,
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.update_documento",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "app.modules.importador.processing_service.crud.add_log",
        lambda *args, **kwargs: None,
    )

    async def fake_extract_text_fn(file_bytes, filename, bypass_cache=False):
        del file_bytes, filename, bypass_cache
        return {
            "text": (
                "FACTURA SIMPLIFICADA\n"
                "ESTABLECIMIENTO: ARCAMPO LOSHMANZANOS\n"
                "NUMERO OPERACION: 00230\n"
                "NUM. TOTAL ART. VENDIDOS = 10\n"
                "B IVA 10,00 2,27 ,23\n"
                "TARJETA\n"
            ),
            "format": "IMAGE_OCR",
            "vision_image_bytes": b"fake-image",
            "ocr_quality_score": 0.61,
        }

    result = asyncio.run(
        process_import_document(
            db=None,
            doc=type("Doc", (), {"id": 1, "tenant_id": None})(),
            tenant_id=None,
            user_id=None,
            file_bytes=b"fake-image",
            filename="doc.jpg",
            tipo_archivo="IMAGE_OCR",
            force=False,
            extract_text_fn=fake_extract_text_fn,
            analyze_document_fn=fake_analyze_document_fn,
            recipe_context=RecipeContext(explicit_recipe_context=True),
        )
    )

    assert called["count"] == 0
    assert result.raw_ai_json["analysis"]["raw_response"] == "reason=low_evidence_visual_review"
    assert result.datos_extraidos == {
        "vendor": "ARCAMPO LOSHMANZANOS",
        "doc_number": "00230",
        "payment_method": "Tarjeta",
    }


@pytest.mark.no_db
def test_infer_total_amount_ignores_item_count_totals():
    lines = [
        "NUM. TOTAL ART. VENDIDOS = 10",
        "NUMERO OPERACION: 00230",
        "IMPORTE MONEDA: 14,33 / eur",
    ]

    assert _infer_total_amount_from_lines(lines) == 14.33


@pytest.mark.no_db
def test_extract_labeled_amount_ignores_total_article_count_context():
    content = """
    NUM. TOTAL ART. VENDIDOS = 10
    TOTAL 14,33
    """.strip()

    assert (
        _extract_labeled_amount(
            content,
            "total_amount",
            prompt_config={"amount_labels": {"total_amount": ["total"]}},
        )
        == 14.33
    )


@pytest.mark.no_db
def test_extract_labeled_amount_ignores_tax_lookahead_into_credit_terms():
    content = """
    IVA 15%
    PLAZO: CREDITO 30 DIAS
    VALOR TOTAL 2145.00
    """.strip()

    assert (
        _extract_labeled_amount(
            content,
            "tax_amount",
            prompt_config={"amount_labels": {"tax_amount": ["iva"]}},
        )
        is None
    )


@pytest.mark.no_db
def test_amount_has_monetary_context_uses_runtime_config(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.load_ocr_runtime_config",
        lambda _db=None: {
            "total_amount_positive_patterns": [r"\bcustomtotal\b"],
            "total_amount_reject_patterns": [],
            "money_currency_tokens": [],
            "money_currency_symbols": [],
        },
    )

    assert (
        _amount_has_monetary_context(
            "CUSTOMTOTAL 14,33",
            14.33,
            field_name="total_amount",
        )
        is True
    )


@pytest.mark.no_db
def test_extract_labeled_amount_uses_runtime_lookahead_tokens(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.load_ocr_runtime_config",
        lambda _db=None: {
            "total_amount_reject_patterns": [],
            "tax_amount_lookahead_required_tokens": ["tributo"],
            "amount_lookahead_reject_tokens": [],
        },
    )

    content = """
    IVA
    tributo 2,46
    """.strip()

    assert (
        _extract_labeled_amount(
            content,
            "tax_amount",
            prompt_config={"amount_labels": {"tax_amount": ["iva"]}},
        )
        == 2.46
    )


@pytest.mark.no_db
def test_infer_total_amount_from_lines_uses_runtime_markers(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.text_fallback_extractor.load_ocr_runtime_config",
        lambda _db=None: {
            "total_amount_reject_patterns": [r"\bblock\b"],
            "total_inference_markers": ["customamount"],
        },
    )

    assert _infer_total_amount_from_lines(["block 99,99", "customamount 12,34"]) == 12.34


@pytest.mark.no_db
def test_noisy_vendor_detection_uses_runtime_config(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_ocr_runtime_config",
        lambda _db=None: {
            "vendor_noise_min_alpha": 1,
            "vendor_noise_min_alpha_ratio": 0.0,
            "vendor_noise_max_weird_ratio": 1.0,
            "vendor_noise_min_strong_tokens": 1,
            "vendor_noise_max_short_tokens": 99,
            "vendor_noise_reject_tokens": ["bloqueado"],
            "vendor_noise_reject_prefixes": [],
            "concept_noise_min_alpha": 5,
            "concept_noise_min_alpha_ratio": 0.40,
            "concept_noise_max_weird_ratio": 0.12,
            "concept_noise_min_strong_tokens": 2,
            "concept_noise_max_short_tokens_factor": 1.0,
            "concept_noise_small_token_max_len": 3,
            "concept_noise_small_token_max_count": 3,
            "concept_noise_reject_chars": ["*", "~", "_", "|", "="],
            "concept_noise_reject_tokens": ["tarjeta", "cambio", "simplif"],
            "concept_noise_reject_prefixes": ["imp.", "imp "],
            "concept_noise_reject_token_pairs": [["base", "cuota"]],
        },
    )

    assert _looks_like_noisy_scalar_text("Proveedor bloqueado real", field_name="vendor") is True


@pytest.mark.no_db
def test_prefer_text_candidate_over_existing_uses_runtime_noise_rules(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_ocr_runtime_config",
        lambda _db=None: {
            "vendor_noise_min_alpha": 1,
            "vendor_noise_min_alpha_ratio": 0.0,
            "vendor_noise_max_weird_ratio": 1.0,
            "vendor_noise_min_strong_tokens": 1,
            "vendor_noise_max_short_tokens": 99,
            "vendor_noise_reject_tokens": ["bloqueado"],
            "vendor_noise_reject_prefixes": [],
            "concept_noise_min_alpha": 5,
            "concept_noise_min_alpha_ratio": 0.40,
            "concept_noise_max_weird_ratio": 0.12,
            "concept_noise_min_strong_tokens": 2,
            "concept_noise_max_short_tokens_factor": 1.0,
            "concept_noise_small_token_max_len": 3,
            "concept_noise_small_token_max_count": 3,
            "concept_noise_reject_chars": ["*", "~", "_", "|", "="],
            "concept_noise_reject_tokens": ["tarjeta", "cambio", "simplif"],
            "concept_noise_reject_prefixes": ["imp.", "imp "],
            "concept_noise_reject_token_pairs": [["base", "cuota"]],
        },
    )

    assert (
        _prefer_text_candidate_over_existing(
            field_name="vendor",
            existing="Proveedor bloqueado real",
            candidate="Proveedor bueno SA",
        )
        is True
    )


@pytest.mark.no_db
def test_extract_vendor_name_from_ocr_rejects_simplified_invoice_header():
    content = """
    FACTURA SIMPLIFICADA
    PARA EL CLIENTE
    ESTABLECIMIENTO: ALCAMPO LOS MANZANOS
    """.strip()

    assert _extract_vendor_name_from_ocr(content) is None


@pytest.mark.no_db
def test_repair_pre_extracted_fields_drops_count_total_and_header_vendor_noise():
    content = """
    FACTURA SIMPLIFICADA
    NUM. TOTAL ART. VENDIDOS = 10
    B IVA 10,00 2,27 ,23
    PARA EL CLIENTE
    """.strip()

    repaired = _repair_pre_extracted_fields(
        {
            "vendor": "FACTURA SIMPLIF eh",
            "total_amount": 10.0,
            "tax_amount": 23.0,
            "concept": "FACTURA SIMPLIF eh",
            "payment_method": "Tarjeta",
        },
        content=content,
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert repaired.get("vendor") in (None, "")
    assert repaired.get("total_amount") in (None, "")


@pytest.mark.no_db
def test_repair_pre_extracted_fields_recovers_invoice_vendor_and_concept_from_line_items():
    content = """
    MOLINOS MIRAFLORES S.A
    RUC: 1890004195001
    FACTURA: 001-001-000120085
    FECHA Y HORA AUTORIZACION: 2026-01-16T08:56:16-05:00
    T-HARINA-00006 0788115386881 50.00 HARINA TRADICION PREMIUM 50 KG F/ 42.90 2145.00
    SUB TOTAL SIN IMPUESTOS 1145
    PLAZO: CREDITO 30 DIAS
    VALOR TOTAL 2145.00
    """.strip()

    repaired = _repair_pre_extracted_fields(
        {
            "line_items": [
                {
                    "description": "IHARINA TRADICION PREMIUM 50 KG F/",
                    "quantity": 50.0,
                    "unit_price": 42.9,
                    "total_price": 2145.0,
                },
                {
                    "description": "HARINA TRADICION PREMIUM 50 KG F/",
                    "quantity": 5.0,
                    "unit_price": 0.0,
                    "total_price": 0.0,
                },
            ],
            "total_amount": 2145.0,
            "concept": "Hul - w._. U",
            "payment_method": "Credito",
            "customer_tax_id": "1890004195001",
        },
        content=content,
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert repaired["vendor"] == "MOLINOS MIRAFLORES S.A"
    assert repaired["concept"] == "HARINA TRADICION PREMIUM 50 KG F/"
    assert repaired["issue_date"] == "2026-01-16"
    assert repaired["vendor_tax_id"] == "1890004195001"
    assert len(repaired["line_items"]) == 1
    assert repaired["line_items"][0]["description"] == "HARINA TRADICION PREMIUM 50 KG F/"
    assert "customer_tax_id" not in repaired
    assert "subtotal" not in repaired
    assert "tax_amount" not in repaired


@pytest.mark.no_db
def test_repair_pre_extracted_fields_strips_secondary_amounts_when_doc_is_not_saveable():
    content = """
    FACTURA SIMPLIFICADA
    ESTABLECIMIENTO: ARCAMPO LOSHMANZANOS
    NUMERO OPERACION: 00230
    NUM. TOTAL ART. VENDIDOS = 10
    B IVA 10,00 2,27 ,23
    TARJETA
    """.strip()

    repaired = _repair_pre_extracted_fields(
        {
            "vendor": "ARCAMPO LOSHMANZANOS",
            "doc_number": "00230",
            "payment_method": "Tarjeta",
            "concept": "icafix*frfi~ufi 5,34",
            "total_amount": 10.0,
            "tax_amount": 23.0,
        },
        content=content,
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert repaired == {
        "vendor": "ARCAMPO LOSHMANZANOS",
        "doc_number": "00230",
        "payment_method": "Tarjeta",
    }


@pytest.mark.no_db
def test_prefer_text_candidate_over_existing_replaces_simplified_header_vendor():
    assert (
        _prefer_text_candidate_over_existing(
            field_name="vendor",
            existing="FAGTURA SIMPLIFTOADA : Z",
            candidate="ALCAMPO LOGRONO",
        )
        is True
    )


@pytest.mark.no_db
def test_extract_fields_from_text_recovers_pos_receipt_metadata():
    text = """
    ALCAMPO LOGRONO
    FACTURA SIMPLIFICADA
    NUECES MONDADAS 2,54 A
    ANACARDOS AUCHAN 2,68 C
    TARJETA 19,39
    CAMBIO 0,00
    PARA EL CLIENTE
    ESTABLECIMIENTO: ALCAMPO LOGRONO
    LOCALIDAD: 26006 LOGRONO
    FECHA - HORA: 27/03/26 - 19:00
    NUMERO OPERACION: 00143
    IMPORTE / MONEDA: 19,39 / eur
    """.strip()

    fields = extract_fields_from_text(
        ocr_text=text,
        canonical_fields={},
        field_aliases={},
        amount_labels={},
        pdf_config={},
        page_texts=None,
    )

    assert fields["vendor"] == "ALCAMPO LOGRONO"
    assert fields["issue_date"] == "2026-03-27"
    assert fields["doc_number"] == "00143"
    assert fields["total_amount"] == 19.39
    assert fields["payment_method"] == "Tarjeta"
    assert fields["concept"] == "NUECES MONDADAS"


@pytest.mark.no_db
def test_extract_fields_from_text_pos_metadata_overrides_header_noise():
    text = """
    ALCAMPO LOGRONO
    FAGTURA SIMPLIFTOADA : Z
    NUECES MONDADAS 2,54 A
    TARJETA 19,39
    PARA EL CLIENTE
    ESTABLECIMIENTO: ALCAMPO LOGRONO
    LOCALTDAD: 26006 LOGRONO
    FECHA - HORA: 27/03/26 - 19:00
    NUMERO OPERACION: 00143
    IMPORTE / MONEDA: 19,39 / eur
    """.strip()

    fields = extract_fields_from_text(
        ocr_text=text,
        canonical_fields={},
        field_aliases={},
        amount_labels={},
        pdf_config={},
        page_texts=None,
    )

    assert fields["vendor"] == "ALCAMPO LOGRONO"
    assert fields["concept"] == "NUECES MONDADAS"


@pytest.mark.no_db
def test_decide_processing_lane_routes_insufficient_text_images_vision_first():
    decision = decide_processing_lane(
        doc_format="IMAGE_OCR",
        has_structured=False,
        has_vision=True,
        text_is_sufficient=False,
        has_semantic_hint=False,
        has_cached_analysis=False,
        is_first_import=True,
        previous_confidence=None,
        deep_reprocess=False,
        processing_cfg={
            "lane_timeout_fast": 12.0,
            "lane_timeout_deep": 90.0,
            "ocr_quality_vision_threshold": 0.45,
        },
        ocr_quality_score=0.20,
    )

    assert decision.lane == "deep"
    assert decision.timeout_secs == 90.0
    assert decision.force_vision is True
    assert decision.vision_first is True
    assert "vision_first" in decision.reasons


@pytest.mark.no_db
def test_analyze_with_context_fast_mode_image_low_quality_still_calls_ai(monkeypatch):
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "INVOICE", "confidence": 0.8, "reasoning": "ai", "fields": {}}

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
    analysis = asyncio.run(
        _analyze_with_context(
            analyze_document_fn=fake_analyze_document_fn,
            content="texto OCR aparentemente suficiente en imagen",
            filename="doc.jpg",
            format_hint="IMAGE_OCR",
            has_structured_rows=False,
            recipe_config=None,
            vision_image_bytes=b"fake-image",
            fallback_patterns={},
            canonical_fields={},
            prompt_config={},
            db=None,
            reprocess_mode="fast",
        )
    )

    # Las imágenes NUNCA saltan IA en fast mode — siempre se analiza con visión
    assert called["count"] == 1
    assert analysis["doc_type"] == "INVOICE"
    assert analysis.get("fast_mode_skip_ai_due_to_sufficient_text") is not True


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
    with pytest.raises(ValueError, match="Imagen de mala calidad"):
        asyncio.run(
            _analyze_with_context(
                analyze_document_fn=fake_analyze_document_fn,
                content="A B",
                filename="foto.jpg",
                format_hint="IMAGE_OCR",
                has_structured_rows=False,
                recipe_config=None,
                vision_image_bytes=b"fake-image",
                fallback_patterns={},
                canonical_fields={},
                prompt_config={},
                db=None,
                reprocess_mode="deep",
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
def test_retry_guard_blocks_timeout_for_same_model_input_and_strategy():
    previous_attempt = _build_ai_attempt_fingerprint(
        model_used="qwen3:8b",
        content="texto OCR de la factura",
        timeout_override=90.0,
        strategy="visual_complex",
        force_vision=True,
    )
    next_attempt = _build_ai_attempt_fingerprint(
        model_used="qwen3:8b",
        content="texto OCR de la factura",
        timeout_override=90.0,
        strategy="visual_complex",
        force_vision=False,
    )

    blocked, reason = _should_skip_useless_retry(
        previous_analysis={"error": "Ollama timeout (90s)"},
        previous_attempt=previous_attempt,
        next_attempt=next_attempt,
    )

    assert blocked is True
    assert reason == "timeout_same_model_input_strategy"


@pytest.mark.no_db
def test_merge_text_fallback_fields_completes_missing_values_without_overwriting():
    base = {
        "vendor": "Distribuidora Integral Andina S.A.",
        "line_items": [],
        "total_amount": 16567.49,
    }
    fallback = {
        "vendor": "Other vendor",
        "issue_date": "2026-04-03",
        "subtotal": 14792.4,
        "tax_amount": 1775.09,
        "line_items": [{"concept": "Aceite", "total_amount": 204.0}],
    }

    changed = _merge_text_fallback_fields(base, fallback)

    assert changed is True
    assert base["vendor"] == "Distribuidora Integral Andina S.A."
    assert base["issue_date"] == "2026-04-03"
    assert base["subtotal"] == 14792.4
    assert base["tax_amount"] == 1775.09
    assert base["total_amount"] == 16567.49
    assert base["line_items"][0]["concept"] == "Aceite"


@pytest.mark.no_db
def test_sanitize_text_fallback_fields_drops_noisy_tax_ids_and_keeps_clean_values():
    fallback = {
        "vendor_tax_id": ":: NORM e T n_n-'buyeme Especial Resolución 04519 . AL 0g _SGs.",
        "customer_tax_id": "1792845612001",
        "customer": "MARIA AURORA CASABAMBA CASABAMBA Boh",
        "issue_date": "2026-04-03",
    }

    cleaned = _sanitize_text_fallback_fields(
        fallback,
        content="texto OCR",
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert "vendor_tax_id" not in cleaned
    assert cleaned["customer_tax_id"] == "1792845612001"
    assert cleaned["customer"] == "MARIA AURORA CASABAMBA CASABAMBA Boh"
    assert cleaned["issue_date"] == "2026-04-03"


@pytest.mark.no_db
def test_sanitize_text_fallback_fields_preserves_rescued_numeric_values_when_repairs_null_them():
    cleaned = _sanitize_text_fallback_fields(
        {"subtotal": 2145.0, "tax_amount": 0.0, "vendor": "Proveedor Demo S.A."},
        content="texto OCR",
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert cleaned["subtotal"] == 2145.0
    assert cleaned["tax_amount"] == 0.0


@pytest.mark.no_db
def test_sanitize_text_fallback_fields_trims_vendor_timestamp_noise():
    cleaned = _sanitize_text_fallback_fields(
        {
            "vendor": "LINOS MIRAFLORES S.A. 2026-01-16T08:56:16-05:00 ga Bins",
            "total_amount": 2145.0,
        },
        content="texto OCR",
        format_hint="IMAGE_OCR",
        prompt_config={},
        ocr_runtime={},
    )

    assert cleaned["vendor"] == "LINOS MIRAFLORES S.A."


@pytest.mark.no_db
def test_invoice_rescue_from_ocr_recovers_missing_invoice_fields():
    text = """
    COMERCIALIZADORA ANDINA S.A.
    RUC: 1792845612001
    FACTURA N° 001-001-000120085
    Fecha: 03/04/2026

    2 Aceite de oliva extra virgen 10.00 20.00
    1 Vinagre balsamico reserva 5.00 5.00

    SUBTOTAL $ 25.00
    IVA 15% $ 3.75
    VALOR TOTAL $ 28.75
    """.strip()

    rescued = invoice_rescue_from_ocr(
        text,
        {
            "vendor_tax_id": "1792845612001",
            "issue_date": "2026-04-03",
            "total_amount": 28.75,
        },
    )

    assert rescued["vendor"] == "COMERCIALIZADORA ANDINA S.A."
    assert rescued["doc_number"] == "001-001-000120085"
    assert rescued["subtotal"] == 25.0
    assert rescued["tax_amount"] == 3.75
    assert len(rescued["line_items"]) == 2
    assert rescued["line_items"][0]["quantity"] == 2.0
    assert rescued["line_items"][0]["total_price"] == 20.0


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


# ── Regresión: bypass determinista para XML_FACTURAE / XML_UBL ────────────────


class TestXmlInvoiceBypassConstants:
    """
    Verifica que los formatos XML de factura electrónica estén correctamente
    incluidos en los sets y mapas que controlan el bypass del LLM.

    Bug: XML_FACTURAE caía en el LLM (que expiraba → confidence 22%, type OTHER)
    porque solo "XML" (genérico) estaba en _STRUCTURED_SKIP_FORMATS.
    """

    def test_xml_facturae_in_structured_skip_formats(self):
        assert "XML_FACTURAE" in _STRUCTURED_SKIP_FORMATS

    def test_xml_ubl_in_structured_skip_formats(self):
        assert "XML_UBL" in _STRUCTURED_SKIP_FORMATS

    def test_xml_facturae_in_xml_invoice_formats(self):
        assert "XML_FACTURAE" in _XML_INVOICE_FORMATS

    def test_xml_ubl_in_xml_invoice_formats(self):
        assert "XML_UBL" in _XML_INVOICE_FORMATS

    def test_tipo_documento_factura_maps_to_invoice(self):
        assert _XML_TIPO_DOCUMENTO_MAP["FACTURA"] == "INVOICE"

    def test_tipo_documento_nota_credito_maps_to_credit_note(self):
        assert _XML_TIPO_DOCUMENTO_MAP["NOTA_CREDITO"] == "CREDIT_NOTE"

    def test_header_fecha_maps_to_issue_date(self):
        assert _XML_HEADER_TO_CANONICAL["fecha"] == "issue_date"

    def test_header_monto_maps_to_total_amount(self):
        assert _XML_HEADER_TO_CANONICAL["monto"] == "total_amount"

    def test_header_proveedor_maps_to_vendor(self):
        assert _XML_HEADER_TO_CANONICAL["proveedor"] == "vendor"

    def test_header_documento_maps_to_doc_number(self):
        assert _XML_HEADER_TO_CANONICAL["documento"] == "doc_number"

    def test_header_ruc_maps_to_vendor_tax_id(self):
        assert _XML_HEADER_TO_CANONICAL["ruc"] == "vendor_tax_id"


class TestXmlInvoiceBypassFieldMapping:
    """
    Verifica la lógica de mapeo de campos XML → campos canónicos que se usa
    en el bloque _skip_ai_for_structured de process_document_logic.
    """

    def test_tipo_documento_unknown_defaults_to_invoice(self):
        """Tipos desconocidos deben defaultear a INVOICE (el tipo más común en XML)."""
        assert _XML_TIPO_DOCUMENTO_MAP.get("DESCONOCIDO", "INVOICE") == "INVOICE"

    def test_all_canonical_keys_are_strings(self):
        """Todos los valores de _XML_HEADER_TO_CANONICAL deben ser strings no vacíos."""
        for xml_key, canonical_key in _XML_HEADER_TO_CANONICAL.items():
            assert (
                isinstance(canonical_key, str) and canonical_key
            ), f"La clave canónica para '{xml_key}' debe ser un string no vacío"

    def test_duplicates_only_in_tax_amount(self):
        """igv e impuesto mapean ambos a tax_amount (alternativas de idioma).
        El código previene sobreescritura con 'if canonical_key not in _xml_fields'.
        No debe haber otros duplicados."""
        from collections import Counter

        counts = Counter(_XML_HEADER_TO_CANONICAL.values())
        allowed_duplicates = {"tax_amount"}
        unexpected = {k for k, v in counts.items() if v > 1 and k not in allowed_duplicates}
        assert not unexpected, f"Duplicados no esperados en _XML_HEADER_TO_CANONICAL: {unexpected}"

    def test_xml_bypass_field_extraction_logic(self):
        """
        Simula manualmente la lógica de extracción de campos del bloque
        _skip_ai_for_structured para XML_FACTURAE, verificando que:
        - Los campos con valores válidos se incluyen
        - Los campos con '0.00' se excluyen
        - El tipo de documento se mapea correctamente
        """
        _xml_meta_kv = {
            "tipo_documento": "FACTURA",
            "fecha": "2025-07-25",
            "documento": "2024-001 A",
            "monto": "0.00",  # debe excluirse
            "subtotal": "0.00",  # debe excluirse
            "proveedor": None,  # debe excluirse (None)
        }
        _EXCLUDES = (None, "", "0", "0.00", "0.0")

        _xml_tipo = str(_xml_meta_kv.get("tipo_documento") or "").upper()
        _hint_doc_type = _XML_TIPO_DOCUMENTO_MAP.get(_xml_tipo, "INVOICE")
        _xml_fields: dict = {}
        for xml_key, canonical_key in _XML_HEADER_TO_CANONICAL.items():
            val = _xml_meta_kv.get(xml_key)
            if val not in _EXCLUDES and canonical_key not in _xml_fields:
                _xml_fields[canonical_key] = val

        assert _hint_doc_type == "INVOICE"
        assert _xml_fields.get("issue_date") == "2025-07-25"
        assert _xml_fields.get("doc_number") == "2024-001 A"
        assert "total_amount" not in _xml_fields
        assert "subtotal" not in _xml_fields
        assert "vendor" not in _xml_fields
