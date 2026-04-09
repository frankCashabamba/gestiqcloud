"""Tests for importador_admin_service helper functions and category_loader.

These tests cover pure utility functions that don't require a database,
focusing on increasing coverage of the new importador_admin_service.py file
and the category_loader module.
"""
from __future__ import annotations

import pytest

from app.modules.importador.category_loader import classify_doc_type, invalidate_cache
from app.modules.importador.services.importador_admin_service import (
    RUNTIME_MODULE_DESCRIPTIONS,
    RUNTIME_MODULE_TITLES,
    _module_description,
    _module_title,
    _normalize_list,
    _value_kind,
)


# ── _module_title ──────────────────────────────────────────────────────────────


def test_module_title_returns_known_title():
    assert _module_title("learning") == "Learning"
    assert _module_title("doc_categories") == "Document Categories"
    assert _module_title("ocr_config") == "OCR Config"
    assert _module_title("ai_runtime") == "AI Runtime"


def test_module_title_fallback_titlecases_unknown():
    assert _module_title("my_custom_module") == "My Custom Module"
    assert _module_title("foo.bar") == "Foo Bar"


def test_module_title_covers_all_known_modules():
    for key, expected in RUNTIME_MODULE_TITLES.items():
        assert _module_title(key) == expected


# ── _module_description ───────────────────────────────────────────────────────


def test_module_description_returns_known_description():
    assert _module_description("doc_categories") is not None
    assert "categor" in _module_description("doc_categories").lower()


def test_module_description_returns_none_for_unknown():
    assert _module_description("totally_unknown_module") is None


def test_module_description_covers_all_described_modules():
    for key in RUNTIME_MODULE_DESCRIPTIONS:
        result = _module_description(key)
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0


# ── _value_kind ───────────────────────────────────────────────────────────────


def test_value_kind_list_when_value_list_provided():
    assert _value_kind("ignored", ["a", "b"]) == "list"
    assert _value_kind(None, ["x"]) == "list"
    assert _value_kind("{}", ["item"]) == "list"


def test_value_kind_json_when_starts_with_brace():
    assert _value_kind('{"key": "val"}', []) == "json"
    assert _value_kind("{}", []) == "json"


def test_value_kind_json_when_starts_with_bracket():
    assert _value_kind("[1, 2, 3]", []) == "json"
    assert _value_kind("[]", []) == "json"


def test_value_kind_text_for_plain_strings():
    assert _value_kind("hello world", []) == "text"
    assert _value_kind("0.85", []) == "text"
    assert _value_kind("true", []) == "text"


def test_value_kind_text_when_none():
    assert _value_kind(None, []) == "text"


def test_value_kind_text_when_empty_string():
    assert _value_kind("", []) == "text"


def test_value_kind_text_when_whitespace_only():
    assert _value_kind("   ", []) == "text"


# ── _normalize_list ───────────────────────────────────────────────────────────


def test_normalize_list_strips_whitespace():
    result = _normalize_list([" hello ", "  world  "])
    assert result == ["hello", "world"]


def test_normalize_list_removes_empty_strings():
    result = _normalize_list(["a", "", "b", "  "])
    assert result == ["a", "b"]


def test_normalize_list_returns_empty_for_none():
    assert _normalize_list(None) == []


def test_normalize_list_returns_empty_for_non_list():
    assert _normalize_list("not_a_list") == []  # type: ignore[arg-type]
    assert _normalize_list(42) == []  # type: ignore[arg-type]


def test_normalize_list_converts_non_string_items():
    result = _normalize_list([1, 2.5, True])
    assert result == ["1", "2.5", "True"]


def test_normalize_list_preserves_order():
    items = ["c", "a", "b"]
    assert _normalize_list(items) == ["c", "a", "b"]


def test_normalize_list_empty_input():
    assert _normalize_list([]) == []


# ── classify_doc_type (category_loader) ──────────────────────────────────────


@pytest.fixture
def sample_categories() -> dict[str, list[str]]:
    return {
        "invoice": ["INVOICE", "FACTURA"],
        "receipt": ["RECEIPT", "RECIBO"],
        "recipe": ["RECIPE", "RECETA"],
    }


def test_classify_doc_type_matches_exact_keyword(sample_categories):
    assert classify_doc_type("INVOICE", sample_categories) == "invoice"
    assert classify_doc_type("RECEIPT", sample_categories) == "receipt"


def test_classify_doc_type_case_insensitive(sample_categories):
    assert classify_doc_type("invoice", sample_categories) == "invoice"
    assert classify_doc_type("Factura", sample_categories) == "invoice"
    assert classify_doc_type("factura electronica", sample_categories) == "invoice"


def test_classify_doc_type_returns_other_for_unknown(sample_categories):
    assert classify_doc_type("NOTA_DEBITO", sample_categories) == "other"
    assert classify_doc_type("UNKNOWN_TYPE", sample_categories) == "other"


def test_classify_doc_type_returns_other_for_empty_string(sample_categories):
    assert classify_doc_type("", sample_categories) == "other"


def test_classify_doc_type_substring_match(sample_categories):
    # "FACTURA" is a substring of "FACTURA ELECTRONICA"
    assert classify_doc_type("FACTURA ELECTRONICA", sample_categories) == "invoice"


def test_classify_doc_type_empty_categories():
    assert classify_doc_type("INVOICE", {}) == "other"


def test_classify_doc_type_category_with_empty_keywords(sample_categories):
    cats = dict(sample_categories)
    cats["empty_cat"] = []
    assert classify_doc_type("INVOICE", cats) == "invoice"


# ── invalidate_cache (category_loader) ───────────────────────────────────────


def test_invalidate_cache_resets_without_error():
    """invalidate_cache should be callable without raising."""
    invalidate_cache()
    # calling it multiple times should also be safe
    invalidate_cache()


# ── Schema: StagingLineSummary properties ─────────────────────────────────────


def test_staging_line_summary_total_and_resolvable():
    from app.modules.importador.schemas import StagingLineSummary

    s = StagingLineSummary(
        pending=2,
        valid=3,
        imported=1,
        invalid=1,
        review=0,
        skipped=0,
        reprocess=1,
    )
    assert s.total == 8
    assert s.resolvable == 4  # pending + invalid + review + reprocess


def test_staging_line_summary_all_zeros():
    from app.modules.importador.schemas import StagingLineSummary

    s = StagingLineSummary()
    assert s.total == 0
    assert s.resolvable == 0


def test_staging_line_summary_only_imported():
    from app.modules.importador.schemas import StagingLineSummary

    s = StagingLineSummary(imported=5)
    assert s.total == 5
    assert s.resolvable == 0


# ── Schema: DocumentRoutingDecision defaults ──────────────────────────────────


def test_document_routing_decision_defaults():
    from app.modules.importador.schemas import DocumentRoutingDecision

    d = DocumentRoutingDecision(document_type="supplier_invoice", confidence=0.9)
    assert d.required_fields_ok is False
    assert d.missing_fields == []
    assert d.suggested_destination is None
    assert d.reason == ""
    assert d.needs_human_review is False
    assert d.source_doc_type is None
    assert d.source_category is None


def test_document_routing_decision_with_all_fields():
    from app.modules.importador.schemas import DocumentRoutingDecision

    d = DocumentRoutingDecision(
        document_type="expense",
        confidence=0.75,
        required_fields_ok=True,
        missing_fields=["vendor"],
        suggested_destination="expense",
        reason="Matched by doc_type rule",
        needs_human_review=True,
        source_doc_type="INVOICE",
        source_category="invoice",
    )
    assert d.document_type == "expense"
    assert d.confidence == 0.75
    assert d.required_fields_ok is True
    assert "vendor" in d.missing_fields
    assert d.suggested_destination == "expense"
    assert d.needs_human_review is True
    assert d.source_doc_type == "INVOICE"


# ── Schema: RoutingProfileAdminIn validation ──────────────────────────────────


def test_routing_profile_admin_in_defaults():
    from app.modules.importador.schemas import RoutingProfileAdminIn

    p = RoutingProfileAdminIn(code="invoice", document_type="supplier_invoice")
    assert p.blocked is False
    assert p.active is True
    assert p.confidence_threshold == 0.8
    assert p.required_groups == []
    assert p.support_fields == []
    assert p.explanation_fields == []


# ── Schema: RuntimeConfigEntryUpsertIn ────────────────────────────────────────


def test_runtime_config_entry_upsert_in_defaults():
    from app.modules.importador.schemas import RuntimeConfigEntryUpsertIn

    u = RuntimeConfigEntryUpsertIn()
    assert u.label is None
    assert u.value_text is None
    assert u.value_list == []


def test_runtime_config_entry_upsert_in_with_list():
    from app.modules.importador.schemas import RuntimeConfigEntryUpsertIn

    u = RuntimeConfigEntryUpsertIn(label="My label", value_list=["a", "b", "c"])
    assert u.label == "My label"
    assert u.value_list == ["a", "b", "c"]


# ── Schema: DashboardStats ────────────────────────────────────────────────────


def test_dashboard_stats_defaults():
    from app.modules.importador.schemas import DashboardStats

    d = DashboardStats()
    assert d.total == 0
    assert d.pendientes == 0
    assert d.en_revision == 0
    assert d.confirmados == 0
    assert d.fallidos == 0


def test_dashboard_stats_with_values():
    from app.modules.importador.schemas import DashboardStats

    d = DashboardStats(total=10, pendientes=3, en_revision=2, confirmados=4, fallidos=1)
    assert d.total == 10
    assert d.pendientes == 3
    assert d.en_revision == 2
    assert d.confirmados == 4
    assert d.fallidos == 1


# ── Schema: SyncRecipeResponse ────────────────────────────────────────────────


def test_sync_recipe_response():
    import uuid

    from app.modules.importador.schemas import SyncRecipeResponse

    r = SyncRecipeResponse(
        recipe_id=uuid.uuid4(),
        recipe_name="Torta de chocolate",
        was_new=True,
        total_cost=25.5,
        ingredients_count=8,
    )
    assert r.recipe_name == "Torta de chocolate"
    assert r.was_new is True
    assert r.total_cost == 25.5
    assert r.ingredients_count == 8


# ── Schema: SyncRecipeSheetResponse ──────────────────────────────────────────


def test_sync_recipe_sheet_response_defaults():
    from app.modules.importador.schemas import SyncRecipeSheetResponse

    r = SyncRecipeSheetResponse(sheet_name="Hoja1", status="created")
    assert r.sheet_name == "Hoja1"
    assert r.status == "created"
    assert r.recipe_id is None
    assert r.was_new is False
    assert r.total_cost == 0
    assert r.ingredients_count == 0
    assert r.message is None


# ── Schema: SyncRecipesResponse ───────────────────────────────────────────────


def test_sync_recipes_response():
    from app.modules.importador.schemas import SyncRecipeSheetResponse, SyncRecipesResponse

    r = SyncRecipesResponse(
        total_sheets=3,
        processed_count=2,
        skipped_count=1,
        results=[
            SyncRecipeSheetResponse(sheet_name="Hoja1", status="created"),
            SyncRecipeSheetResponse(sheet_name="Hoja2", status="skipped"),
        ],
    )
    assert r.total_sheets == 3
    assert r.processed_count == 2
    assert r.skipped_count == 1
    assert len(r.results) == 2


# ── Schema: IterationScopeIn ──────────────────────────────────────────────────


def test_iteration_scope_in_defaults():
    from app.modules.importador.schemas import IterationScopeIn

    s = IterationScopeIn()
    assert s.mode == "ALL"
    assert s.filter_estados == []
    assert s.filter_error_codes == []
    assert s.filter_campos == []
    assert s.filter_columns == []
    assert s.filter_lines == []
    assert s.filter_sheet is None


def test_iteration_scope_in_selective():
    from app.modules.importador.schemas import IterationScopeIn

    s = IterationScopeIn(
        mode="SELECTIVE",
        filter_estados=["INVALID", "REPROCESS"],
        filter_lines=[1, 2, 3],
        filter_sheet="Sheet1",
    )
    assert s.mode == "SELECTIVE"
    assert "INVALID" in s.filter_estados
    assert s.filter_lines == [1, 2, 3]
    assert s.filter_sheet == "Sheet1"


# ── Schema: RunIterationRequest ───────────────────────────────────────────────


def test_run_iteration_request_defaults():
    from app.modules.importador.schemas import RunIterationRequest

    r = RunIterationRequest()
    assert r.scope.mode == "ALL"
    assert r.scope.filter_estados == []


# ── Schema: SaveDocumentRequest ───────────────────────────────────────────────


def test_save_document_request_defaults():
    from app.modules.importador.schemas import SaveDocumentRequest

    r = SaveDocumentRequest()
    assert r.destination is None
    assert r.payment_status == "pending"
    assert r.paid_amount is None
    assert r.update_stock is False
    assert r.warehouse_id is None
    assert r.line_matches == []


def test_save_document_request_with_destination():
    from app.modules.importador.schemas import SaveDocumentRequest

    r = SaveDocumentRequest(
        destination="expense",
        payment_status="paid",
        paid_amount=100.0,
        notes="Test note",
    )
    assert r.destination == "expense"
    assert r.payment_status == "paid"
    assert r.paid_amount == 100.0
    assert r.notes == "Test note"


# ── Schema: SaveDocumentLineMatch ─────────────────────────────────────────────


def test_save_document_line_match_defaults():
    from app.modules.importador.schemas import SaveDocumentLineMatch

    m = SaveDocumentLineMatch(line_index=0)
    assert m.line_index == 0
    assert m.product_id is None
    assert m.persist_alias is True
    assert m.create_new is False


# ── Schema: ReviewSessionCreate ───────────────────────────────────────────────


def test_review_session_create_defaults():
    from app.modules.importador.schemas import ReviewSessionCreate

    r = ReviewSessionCreate()
    assert r.filter_estados == []
    assert r.filter_error_codes == []
    assert r.filter_campos == []
    assert r.filter_columns == []
    assert r.filter_lines == []
    assert r.filter_sheet is None


# ── Schema: StagingLinePatch ──────────────────────────────────────────────────


def test_staging_line_patch_defaults():
    from app.modules.importador.schemas import StagingLinePatch

    p = StagingLinePatch()
    assert p.estado is None
    assert p.campos_revision is None
    assert p.normalized_data is None


def test_staging_line_patch_with_estado():
    from app.modules.importador.schemas import StagingLinePatch

    p = StagingLinePatch(estado="REPROCESS", campos_revision=["field_a", "field_b"])
    assert p.estado == "REPROCESS"
    assert p.campos_revision == ["field_a", "field_b"]


# ── Schema: ConfirmRequest / EditFieldsRequest ────────────────────────────────


def test_confirm_request():
    from app.modules.importador.schemas import ConfirmRequest

    r = ConfirmRequest(datos_confirmados={"vendor": "Proveedor SA", "total": 100.0})
    assert r.datos_confirmados["vendor"] == "Proveedor SA"


def test_edit_fields_request():
    from app.modules.importador.schemas import EditFieldsRequest

    r = EditFieldsRequest(campos={"total_amount": 250.0, "currency": "USD"})
    assert r.campos["total_amount"] == 250.0
    assert r.campos["currency"] == "USD"


# ── Schema: SaveDailyLogRequest / SaveDailyLogResponse ───────────────────────


def test_save_daily_log_request_defaults():
    from app.modules.importador.schemas import SaveDailyLogRequest

    r = SaveDailyLogRequest()
    assert r.log_date is None


def test_save_daily_log_request_with_date():
    from app.modules.importador.schemas import SaveDailyLogRequest

    r = SaveDailyLogRequest(log_date="2026-04-01")
    assert r.log_date == "2026-04-01"


def test_save_daily_log_response():
    from app.modules.importador.schemas import SaveDailyLogResponse

    r = SaveDailyLogResponse(log_date="2026-04-01", inserted=5, matched_recipes=3)
    assert r.log_date == "2026-04-01"
    assert r.inserted == 5
    assert r.matched_recipes == 3
    assert r.unmatched_products == []


# ── Schema: SaveProductsFromDocumentRequest / Response ───────────────────────


def test_save_products_from_document_request_defaults():
    from app.modules.importador.schemas import SaveProductsFromDocumentRequest

    r = SaveProductsFromDocumentRequest()
    assert r.sheet_name is None
    assert r.row_indexes == []
    assert r.category_name is None


def test_save_products_from_document_response_defaults():
    from app.modules.importador.schemas import SaveProductsFromDocumentResponse

    r = SaveProductsFromDocumentResponse()
    assert r.created == 0
    assert r.updated == 0
    assert r.skipped_existing == 0
    assert r.skipped_invalid == 0
    assert r.product_ids == []
    assert r.skipped_names == []


# ── Schema: RoutingRuleAdminIn ────────────────────────────────────────────────


def test_routing_rule_admin_in_tenant_scope():
    import uuid

    from app.modules.importador.schemas import RoutingRuleAdminIn

    r = RoutingRuleAdminIn(
        scope_kind="tenant",
        tenant_id=uuid.uuid4(),
        source_kind="doc_type",
        source_key="INVOICE",
        profile_code="supplier_invoice",
        priority=10,
    )
    assert r.scope_kind == "tenant"
    assert r.source_kind == "doc_type"
    assert r.source_key == "INVOICE"
    assert r.profile_code == "supplier_invoice"
    assert r.active is True


def test_routing_rule_admin_in_sector_scope():
    from app.modules.importador.schemas import RoutingRuleAdminIn

    r = RoutingRuleAdminIn(
        scope_kind="sector",
        sector="panaderia",
        source_kind="category",
        source_key="invoice",
        profile_code="supplier_invoice",
    )
    assert r.scope_kind == "sector"
    assert r.sector == "panaderia"
    assert r.source_kind == "category"


# ── Schema: RoutingPreviewRequest ─────────────────────────────────────────────


def test_routing_preview_request_defaults():
    from app.modules.importador.schemas import RoutingPreviewRequest

    r = RoutingPreviewRequest()
    assert r.scope_kind == "system"
    assert r.document_id is None
    assert r.tenant_id is None
    assert r.ai_confidence == 0.85
    assert r.extracted_data == {}
    assert r.requires_review is False
    assert r.destination_override is None


# ── Schema: DocumentReviewHintOut ────────────────────────────────────────────


def test_document_review_hint_out_defaults():
    from app.modules.importador.schemas import DocumentReviewHintOut

    h = DocumentReviewHintOut(field="total_amount")
    assert h.field == "total_amount"
    assert h.field_type == "text"
    assert h.priority == 1
    assert h.is_missing is False
    assert h.corrected_count == 0
    assert h.confirmed_examples == []
    assert h.last_confirmed_value is None
    assert h.reason == ""


# ── Schema: AssistedReviewOut ─────────────────────────────────────────────────


def test_assisted_review_out():
    from app.modules.importador.schemas import AssistedReviewOut

    a = AssistedReviewOut(
        mode="assisted_lines",
        reason="Line items detected",
        line_items_count=5,
        scalar_fields_detected=3,
        can_derive_total=True,
    )
    assert a.mode == "assisted_lines"
    assert a.line_items_count == 5
    assert a.can_derive_total is True


# ── Schema: RuntimeConfigCatalogOut / RuntimeConfigModuleOut ─────────────────


def test_runtime_config_catalog_out_defaults():
    from app.modules.importador.schemas import RuntimeConfigCatalogOut

    c = RuntimeConfigCatalogOut()
    assert c.modules == []


def test_runtime_config_module_out_defaults():
    from app.modules.importador.schemas import RuntimeConfigModuleOut

    m = RuntimeConfigModuleOut(module="learning", title="Learning")
    assert m.module == "learning"
    assert m.title == "Learning"
    assert m.description is None
    assert m.editable is True
    assert m.entries == []


# ── Schema: RoutingLearningInsightOut defaults ────────────────────────────────


def test_routing_learning_insight_out_defaults():
    from app.modules.importador.schemas import RoutingLearningInsightOut

    r = RoutingLearningInsightOut(
        source_doc_type="INVOICE",
        document_type="supplier_invoice",
    )
    assert r.source_doc_type == "INVOICE"
    assert r.document_type == "supplier_invoice"
    assert r.signals_count == 0
    assert r.save_count == 0
    assert r.confirm_count == 0
    assert r.edit_count == 0
    assert r.top_missing_fields == []
    assert r.top_changed_fields == []
    assert r.suggested_required_groups == []
    assert r.suggested_support_fields == []
    assert r.suggested_confidence_threshold == 0.8
    assert r.avg_success_confidence == 0.0
    assert r.notes == []


# ── Schema: ProductMatchCandidateOut / DocumentLineMatchOut ──────────────────


def test_product_match_candidate_out():
    import uuid

    from app.modules.importador.schemas import ProductMatchCandidateOut

    c = ProductMatchCandidateOut(
        product_id=uuid.uuid4(),
        name="Harina de trigo",
        unit="kg",
        score=0.92,
        reason="fuzzy_match",
    )
    assert c.name == "Harina de trigo"
    assert c.score == 0.92
    assert c.inferred_factor == 1
    assert c.sku is None
    assert c.stock == 0


def test_document_line_match_out_defaults():
    from app.modules.importador.schemas import DocumentLineMatchOut

    m = DocumentLineMatchOut(line_index=0, description="Harina")
    assert m.line_index == 0
    assert m.description == "Harina"
    assert m.quantity == 0
    assert m.unit_price == 0
    assert m.selected_product_id is None
    assert m.candidates == []
    assert m.inferred_factor == 1


# ── Schema: DocumentLineMatchesResponse ──────────────────────────────────────


def test_document_line_matches_response_empty():
    from app.modules.importador.schemas import DocumentLineMatchesResponse

    r = DocumentLineMatchesResponse()
    assert r.lines == []


# ── Schema: ImportadorRoutingOverviewOut ──────────────────────────────────────


def test_importador_routing_overview_out():
    import uuid

    from app.modules.importador.schemas import DashboardStats, ImportadorRoutingOverviewOut

    o = ImportadorRoutingOverviewOut(
        tenant_id=uuid.uuid4(),
        tenant_name="Test Tenant",
        dashboard=DashboardStats(total=5),
    )
    assert o.tenant_name == "Test Tenant"
    assert o.dashboard.total == 5
    assert o.recent_batches == []
    assert o.recent_documents == []
    assert o.reprocess_queue == []
    assert o.learning_insights == []
