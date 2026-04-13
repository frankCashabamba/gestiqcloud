from __future__ import annotations

import asyncio

import pytest

from app.modules.importador.processing_service import (
    _XML_HEADER_TO_CANONICAL,
    _XML_INVOICE_FORMATS,
    _XML_TIPO_DOCUMENTO_MAP,
    _STRUCTURED_SKIP_FORMATS,
    _analysis_indicates_ai_failure,
    _analyze_with_context,
    _build_ai_attempt_fingerprint,
    _build_table_prompt_preview,
    _merge_text_fallback_fields,
    _pre_extract_route_decision,
    _should_skip_useless_retry,
    _sanitize_text_fallback_fields,
)
from app.modules.importador.invoice_ocr_rescue import invoice_rescue_from_ocr
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
def test_analyze_with_context_fast_mode_image_calls_ai_when_ocr_is_sufficient(monkeypatch):
    """Imágenes (vision_image_bytes set) SIEMPRE llaman a la IA, incluso en fast mode.
    El OCR extrae texto pero pierde layout, logos y sellos que el modelo de visión sí ve."""
    called = {"count": 0}

    async def fake_analyze_document_fn(*args, **kwargs):
        del args, kwargs
        called["count"] += 1
        return {"doc_type": "INVOICE", "confidence": 0.82, "reasoning": "ai", "fields": {"total_amount": 10}}

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

    analysis = asyncio.run(
        _analyze_with_context(
            analyze_document_fn=fake_analyze_document_fn,
            content="texto OCR suficientemente largo y limpio para resolver el documento",
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

    # Las imágenes siempre llaman a la IA, incluso en fast mode con texto suficiente
    assert called["count"] == 1
    assert analysis["doc_type"] == "INVOICE"
    assert analysis["confidence"] == 0.82


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
    monkeypatch.setattr(
        "app.modules.importador.processing_service.load_ai_runtime_config",
        lambda _db=None: {
            "ocr_min_quality": 0.95,
            "openai_fallback_ocr_quality_threshold": 0.95,
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
        ai_runtime={"ocr_evidence_formats": ["IMAGE_OCR"]},
        ocr_runtime={},
    )

    assert "vendor_tax_id" not in cleaned
    assert cleaned["customer_tax_id"] == "1792845612001"
    assert cleaned["customer"] == "MARIA AURORA CASABAMBA CASABAMBA Boh"
    assert cleaned["issue_date"] == "2026-04-03"


@pytest.mark.no_db
def test_sanitize_text_fallback_fields_preserves_rescued_numeric_values_when_repairs_null_them(
    monkeypatch,
):
    monkeypatch.setattr(
        "app.modules.importador.processing_service._apply_high_evidence_ocr_repairs",
        lambda parsed, **kwargs: parsed["fields"].update({"subtotal": None, "tax_amount": None}),
    )

    cleaned = _sanitize_text_fallback_fields(
        {"subtotal": 2145.0, "tax_amount": 0.0, "vendor": "Proveedor Demo S.A."},
        content="texto OCR",
        format_hint="IMAGE_OCR",
        prompt_config={},
        ai_runtime={"ocr_evidence_formats": ["IMAGE_OCR"]},
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
        ai_runtime={"ocr_evidence_formats": ["IMAGE_OCR"]},
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
            assert isinstance(canonical_key, str) and canonical_key, (
                f"La clave canónica para '{xml_key}' debe ser un string no vacío"
            )

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
            "monto": "0.00",       # debe excluirse
            "subtotal": "0.00",    # debe excluirse
            "proveedor": None,     # debe excluirse (None)
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
