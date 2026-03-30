from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.modules.importador.ai_classifier import analyze_document


def test_analyze_document_uses_runtime_prompt_config_and_canonical_fields(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_query(**kwargs):
        captured["prompt"] = kwargs["prompt"]
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
