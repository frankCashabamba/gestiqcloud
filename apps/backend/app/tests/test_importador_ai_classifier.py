from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.modules.importador.ai_classifier import _fallback_classify, analyze_document


def test_analyze_document_uses_runtime_prompt_config_and_canonical_fields(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        captured["messages"] = kwargs.get("messages")
        return SimpleNamespace(
            content=(
                '{"doc_type":"INVOICE","confidence":0.93,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{"vendor":"ACME"}}'
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="Factura proveedor ACME por 2145.00",
            filename="factura.pdf",
            format_hint="PDF",
            canonical_fields={
                "vendor": {"type": "text"},
                "issue_date": {"type": "date"},
                "total_amount": {"type": "numeric"},
            },
            prompt_config={
                "extraction_system": "System from DB",
                "doc_type_instruction": "Configured doc type from DB",
                "critical_rules": ["Rule from DB"],
            },
        )
    )

    assert result["doc_type"] == "INVOICE"
    assert result["model_used"] == "test-model"
    assert "System from DB" in captured["prompt"]
    assert '"doc_type": "Configured doc type from DB"' in captured["prompt"]
    assert "Rule from DB" in captured["prompt"]
    assert '"issue_date": "YYYY-MM-DD or null"' in captured["prompt"]
    assert '"total_amount": NUMBER or null' in captured["prompt"]
    assert result["prompt_full"].startswith("System from DB")
    assert result["prompt_parts"]["mode"] == "text"
    assert result["prompt_parts"]["system_prompt"] == "System from DB"
    assert result["prompt_parts"]["doc_type_instruction"] == "Configured doc type from DB"
    assert result["prompt_parts"]["critical_rules"][0] == "Rule from DB"
    assert captured["messages"] == [
        {"role": "system", "content": "System from DB"},
        {"role": "user", "content": result["prompt_parts"]["user_prompt"]},
    ]


def test_analyze_document_uses_runtime_doc_type_instruction_for_structured_inputs(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            content='{"doc_type":"PRICE_LIST","confidence":0.88,"reasoning":"ok"}',
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="sku,price\nA1,9.99",
            filename="lista.csv",
            format_hint="CSV",
            has_structured_rows=True,
            prompt_config={
                "doc_type_instruction": "Use DB labels only for structured previews.",
            },
        )
    )

    assert result["doc_type"] == "PRICE_LIST"
    assert "Use DB labels only for structured previews." in captured["prompt"]
    assert result["prompt_parts"]["mode"] == "structured_classification"
    assert (
        result["prompt_parts"]["doc_type_instruction"]
        == "Use DB labels only for structured previews."
    )


def test_analyze_document_uses_split_prompt_labels_from_runtime_config(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            content='{"doc_type":"INVOICE","confidence":0.88,"reasoning":"ok","is_table":false,"columns":[],"fields":{}}',
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="Documento de prueba",
            filename="doc.pdf",
            format_hint="PDF",
            canonical_fields=None,
            prompt_config={
                "extraction_system": "System cfg",
                "response_json_label": "JSON SOLO:",
                "critical_rules_heading": "REGLAS DURAS:",
                "additional_instructions_heading": "EXTRA:",
                "critical_rules": ["Regla A"],
            },
            recipe_config={"prompt_user": "Usa concepto contable corto."},
        )
    )

    assert "JSON SOLO:" in captured["prompt"]
    assert "REGLAS DURAS:" in captured["prompt"]
    assert "EXTRA:" in captured["prompt"]
    assert result["prompt_parts"]["custom_user_prompt"] == "Usa concepto contable corto."
    assert result["prompt_parts"]["full_prompt"] == result["prompt_full"]


def test_analyze_document_uses_runtime_time_context_template(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            content='{"doc_type":"INVOICE","confidence":0.88,"reasoning":"ok","is_table":false,"columns":[],"fields":{}}',
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="Documento de prueba",
            filename="doc.pdf",
            format_hint="PDF",
            canonical_fields=None,
            prompt_config={
                "extraction_system": "System cfg",
                "document_time_context_template": "VENTANA {previous_year}/{current_year}",
                "critical_rules": ["Regla A"],
            },
        )
    )

    assert "VENTANA" in captured["prompt"]
    assert "VENTANA" in result["prompt_parts"]["user_prompt"]


def test_analyze_document_uses_runtime_fallback_dynamic_fields_prompt(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
        return SimpleNamespace(
            content='{"doc_type":"INVOICE","confidence":0.88,"reasoning":"ok","is_table":false,"columns":[],"fields":{}}',
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.load_prompt_config",
        lambda _db=None: {
            "extraction_system": "System from seed",
            "doc_type_instruction": "Configured type from seed",
            "critical_rules": ["Rule from seed"],
            "fallback_dynamic_fields_prompt": '    "custom_field": "from runtime seed"',
        },
    )

    result = asyncio.run(
        analyze_document(
            content="Documento con campos genericos",
            filename="doc.pdf",
            format_hint="PDF",
            canonical_fields=None,
            prompt_config=None,
        )
    )

    assert result["doc_type"] == "INVOICE"
    assert '"custom_field": "from runtime seed"' in captured["prompt"]
    assert "System from seed" in captured["prompt"]


def test_analyze_document_passes_openai_fallback_policy_context(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_query(**kwargs):
        captured["context"] = kwargs.get("context")
        return SimpleNamespace(
            content='{"doc_type":"INVOICE","confidence":0.88,"reasoning":"ok","is_table":false,"columns":[],"fields":{}}',
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="Factura proveedor ACME con total 123.45",
            filename="factura.pdf",
            format_hint="PDF",
            canonical_fields={"vendor": {"type": "text"}},
        )
    )

    policy_context = captured["context"]["ai_fallback_policy"]
    assert policy_context["enabled"] is True
    assert policy_context["allow_on_error"] is False
    assert policy_context["allow_on_slow"] is True
    assert policy_context["allow_on_complex"] is True
    assert policy_context["prompt_chars"] == len(result["prompt_full"])
    assert policy_context["complexity_score"] >= 0.0
    assert "reasons" in policy_context


def test_fallback_classify_uses_runtime_doc_type_patterns(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.load_doc_type_patterns",
        lambda _db=None: {"DELIVERY_NOTE": ["albaran", "delivery note"]},
    )

    result = _fallback_classify("Documento ALBARAN con entrega", "entrega.txt")

    assert result["doc_type"] == "DELIVERY_NOTE"
    assert result["confidence"] > 0.2


def test_analyze_document_blanks_low_evidence_fields_for_weak_image_ocr(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"SUPPLIER_INVOICE","confidence":0.94,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{'
                '"vendor":"Empresa X",'
                '"customer":"Cliente A",'
                '"doc_number":"INV-001",'
                '"issue_date":"2025-10-15",'
                '"currency":"USD",'
                '"payment_terms":"30 dias",'
                '"subtotal":750.0,'
                '"tax_amount":127.5,'
                '"total_amount":877.5,'
                '"line_items":[{"description":"Mantenimiento preventivo","quantity":1,"unit_price":300.0,"total_price":300.0}]'
                "}}"
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content=(
                "FECHA CLIENTE NOTA VENTA DIRECCION CIUDAD RUC CANT DESCRIPCION VTOTAL "
                "Big 225 Ci frut 1700 Ci frut 1000 Amper 535 530 530"
            ),
            filename="nota-venta.jpg",
            format_hint="IMAGE_OCR",
            image_bytes=None,
            canonical_fields={
                "vendor": {"type": "text"},
                "customer": {"type": "text"},
                "doc_number": {"type": "text"},
                "issue_date": {"type": "date"},
                "currency": {"type": "text"},
                "payment_terms": {"type": "text"},
                "subtotal": {"type": "numeric"},
                "tax_amount": {"type": "numeric"},
                "total_amount": {"type": "numeric"},
                "line_items": {"type": "list"},
            },
        )
    )

    assert result["doc_type"] == "SUPPLIER_INVOICE"
    assert result["fields"]["vendor"] is None
    assert result["fields"]["customer"] is None
    assert result["fields"]["doc_number"] is None
    assert result["fields"]["issue_date"] is None
    assert result["fields"]["currency"] is None
    assert result["fields"]["payment_terms"] is None
    assert result["fields"]["subtotal"] is None
    assert result["fields"]["tax_amount"] is None
    assert result["fields"]["total_amount"] is None
    assert result["fields"]["line_items"] == []
    assert result["confidence"] == 0.45
    assert "Low OCR evidence" in result["reasoning"]


def test_analyze_document_uses_runtime_ai_guard_config(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"SUPPLIER_INVOICE","confidence":0.94,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{"vendor":"Inventado"}}'
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)
    monkeypatch.setattr(
        "app.modules.importador.ai_classifier.load_ai_runtime_config",
        lambda _db=None: {
            "ocr_min_quality": 0.9,
            "ocr_min_words_for_vision": 999,
            "ocr_length_target_chars": 1200,
            "ocr_word_target": 180,
            "ocr_alpha_ratio_target": 0.6,
            "ocr_noise_ratio_limit": 0.2,
            "ocr_score_weight_length": 0.35,
            "ocr_score_weight_words": 0.35,
            "ocr_score_weight_alpha": 0.2,
            "ocr_score_weight_clean": 0.1,
            "ocr_guard_confidence_cap": 0.33,
            "ocr_evidence_formats": ["IMAGE_OCR"],
            "vision_allowed_formats": ["IMAGE_OCR"],
            "vision_resize_max_dim": 1024,
            "vision_temperature": 0.1,
            "vision_num_predict": 600,
            "vision_probe_timeout_seconds": 5.0,
            "vision_timeout_seconds": 45.0,
        },
    )

    result = asyncio.run(
        analyze_document(
            content="OCR muy pobre sin evidencia real",
            filename="nota.jpg",
            format_hint="IMAGE_OCR",
            image_bytes=None,
            canonical_fields={"vendor": {"type": "text"}},
        )
    )

    assert result["fields"]["vendor"] is None
    assert result["confidence"] == 0.33


def test_analyze_document_preserves_fields_when_image_ocr_has_evidence(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"SUPPLIER_INVOICE","confidence":0.94,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{'
                '"vendor":"Molinos Miraflores",'
                '"doc_number":"INV16012026",'
                '"issue_date":"2026-01-16",'
                '"currency":"USD",'
                '"total_amount":2145.0'
                "}}"
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content=(
                "Factura proveedor Molinos Miraflores doc INV16012026 fecha 2026 01 16 "
                "total usd 2145 00 pago credito"
            ),
            filename="factura.jpg",
            format_hint="IMAGE_OCR",
            image_bytes=None,
            canonical_fields={
                "vendor": {"type": "text"},
                "doc_number": {"type": "text"},
                "issue_date": {"type": "date"},
                "currency": {"type": "text"},
                "total_amount": {"type": "numeric"},
            },
        )
    )

    assert result["fields"]["vendor"] == "Molinos Miraflores"
    assert result["fields"]["doc_number"] == "INV16012026"
    assert result["fields"]["issue_date"] == "2026-01-16"
    assert result["fields"]["currency"] == "USD"
    assert result["fields"]["total_amount"] == 2145.0
    assert result["confidence"] == 0.94


def test_analyze_document_repairs_total_and_date_from_explicit_ocr_labels(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"INVOICE","confidence":0.9,"reasoning":"ok",'
                '"is_table":true,"columns":["Product"],"fields":{'
                '"issue_date":"2028-01-16",'
                '"subtotal":85.8,'
                '"tax_amount":12.87,'
                '"total_amount":98.67'
                "}}"
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content=(
                "LINOS MIRAFLORES S.A.\n"
                "2026-01-16T08:56:16-05:00\n"
                "Fecha de Emision : viernes, 16 de enero de 2026\n"
                "SUB TOTAL 0% 2,145.00\n"
                "IVA 15% 0.00\n"
                "VALOR TOTAL 2,145.00\n"
            ),
            filename="factura.jpg",
            format_hint="IMAGE_OCR",
            image_bytes=None,
            canonical_fields={
                "issue_date": {"type": "date"},
                "subtotal": {"type": "numeric"},
                "tax_amount": {"type": "numeric"},
                "total_amount": {"type": "numeric"},
            },
        )
    )

    assert result["fields"]["issue_date"] == "2026-01-16"
    assert result["fields"]["subtotal"] == 2145.0
    assert result["fields"]["tax_amount"] == 0.0
    assert result["fields"]["total_amount"] == 2145.0


def test_analyze_document_repairs_pdf_invoice_fields_from_ocr_context(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"INVOICE","confidence":0.91,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{'
                '"vendor":"Distribuidora Integral Andina S.A.",'
                '"issue_date":"2026-01-01",'
                '"total_amount":1284.0,'
                '"currency":"USD"'
                "}}"
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content=(
                "FACTURA DE PROVEEDOR\n"
                "Proveedor\n"
                "Distribuidora Integral Andina S.A.\n"
                "RUC: 1792845612001\n"
                "Fecha de emision: 03/04/2026\n"
                "Subtotal\n"
                "$ 14,792.40\n"
                "IVA 12%\n"
                "$ 1,775.09\n"
                "Total\n"
                "$ 16,567.49\n"
            ),
            filename="factura-proveedor.pdf",
            format_hint="PDF",
            canonical_fields={
                "vendor": {"type": "text"},
                "vendor_tax_id": {"type": "text"},
                "issue_date": {"type": "date"},
                "total_amount": {"type": "numeric"},
                "currency": {"type": "text"},
            },
        )
    )

    assert result["fields"]["vendor"] == "Distribuidora Integral Andina S.A."
    assert result["fields"]["vendor_tax_id"] == "1792845612001"
    assert result["fields"]["issue_date"] == "2026-04-03"
    assert result["fields"]["total_amount"] == 16567.49
    assert result["fields"]["currency"] == "USD"


def test_analyze_document_rebuilds_line_item_extra_columns_from_ocr(monkeypatch):
    async def fake_query(**kwargs):
        del kwargs
        return SimpleNamespace(
            content=(
                '{"doc_type":"INVOICE","confidence":0.9,"reasoning":"ok",'
                '"is_table":false,"columns":[],"fields":{"line_items":['
                '{"description":"Set de tazas de ceramica 350 ml","quantity":24,"unit_price":2.35,"total_price":56.40},'
                '{"description":"Caja organizadora plastica mediana","quantity":18,"unit_price":4.80,"total_price":86.40}'
                "]}}"
            ),
            model="test-model",
            is_error=False,
            error=None,
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content=(
                "Articulo\n"
                "Ref.\n"
                "Cant.\n"
                "Precio ud.\n"
                "Importe\n"
                "Set de tazas de ceramica 350 ml\n"
                "REF-BZ-1042\n"
                "24\n"
                "2,35 €\n"
                "56,40 €\n"
                "Caja organizadora plastica mediana\n"
                "REF-HG-2210\n"
                "18\n"
                "4,80 €\n"
                "86,40 €\n"
            ),
            filename="factura-bazar.pdf",
            format_hint="PDF_OCR",
            canonical_fields={"line_items": {"type": "list"}},
        )
    )

    line_items = result["fields"]["line_items"]
    assert line_items[0]["extra_columns"]["Ref."] == "REF-BZ-1042"
    assert line_items[1]["extra_columns"]["Ref."] == "REF-HG-2210"


def test_analyze_document_bypasses_ai_for_structured_payload(monkeypatch):
    called = {"count": 0}

    async def fake_query(**kwargs):
        called["count"] += 1
        raise AssertionError("AIService.query should not run for structured payloads")

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="sku,qty\nA1,2",
            filename="inventario.csv",
            format_hint="CSV",
            has_structured_rows=True,
            structured_data=[
                {"sku": "A1", "qty": 2},
                {"sku": "B2", "qty": 4},
            ],
            structured_metadata={
                "sheet_1": {
                    "warehouse": "Central",
                }
            },
            recipe_config={
                "doc_type_hint": "INVENTORY",
                "doc_type_hint_confidence": 0.91,
            },
            fallback_patterns={},
        )
    )

    assert called["count"] == 0
    assert result["model_used"] == "structured-direct"
    assert result["doc_type"] == "INVENTORY"
    assert result["is_table"] is True
    assert result["fields"]["line_items"][0]["sku"] == "A1"
    assert result["fields"]["warehouse"] == "Central"


def test_analyze_document_deep_mode_uses_ai_for_structured_payload(monkeypatch):
    captured: dict[str, object] = {"count": 0}

    async def fake_query(**kwargs):
        captured["count"] += 1
        captured["bypass_cache"] = kwargs.get("bypass_cache")
        captured["prompt"] = kwargs.get("prompt")
        return SimpleNamespace(
            content='{"doc_type":"INVENTORY","confidence":0.86,"reasoning":"deep","is_table":true,"columns":[],"fields":{"line_items":[{"sku":"A1","qty":2}]}}',
            model="test-model",
            is_error=False,
            error=None,
            metadata={"source": "provider"},
        )

    monkeypatch.setattr("app.modules.importador.ai_classifier.AIService.query", fake_query)

    result = asyncio.run(
        analyze_document(
            content="sku,qty\nA1,2",
            filename="inventario.csv",
            format_hint="CSV",
            structured_data=[
                {"sku": "A1", "qty": 2},
                {"sku": "B2", "qty": 4},
            ],
            structured_metadata={
                "sheet_1": {
                    "warehouse": "Central",
                }
            },
            recipe_config={
                "doc_type_hint": "INVENTORY",
                "doc_type_hint_confidence": 0.91,
            },
            fallback_patterns={},
            reprocess_mode="deep",
            deep_reprocess_context={
                "previous_doc_type": "INVENTORY",
                "previous_confidence": 0.54,
            },
            deep_focus_fields=["total_amount", "vendor"],
        )
    )

    assert captured["count"] == 1
    assert captured["bypass_cache"] is True
    assert result["doc_type"] == "INVENTORY"
    assert result["cache_bypassed"] is True
    assert result["fields"]["line_items"][0]["sku"] == "A1"
