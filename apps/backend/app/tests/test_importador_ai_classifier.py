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
