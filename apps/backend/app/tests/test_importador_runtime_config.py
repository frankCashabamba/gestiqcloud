from __future__ import annotations

from app.modules.importador import pre_classifier
from app.modules.importador.runtime_config import (
    invalidate_runtime_config_cache,
    load_doc_categories_config,
    load_filename_normalization_config,
    load_pre_classifier_runtime_config,
    load_prompt_config,
    load_routing_fallback_profiles_config,
    load_routing_fallback_rules_config,
    load_routing_field_aliases,
    load_routing_field_labels,
    load_tax_id_patterns_config,
)


def test_runtime_config_loads_pre_classifier_seed_defaults():
    invalidate_runtime_config_cache()

    config = load_pre_classifier_runtime_config(None)

    assert config["min_header_confirmations"] == 2.0
    assert config["filename_min_confidence"] == 0.70
    assert config["header_coverage_min_ratio"] == 0.50
    assert config["structured_skip_threshold"] == 0.75
    assert config["ocr_weird_ratio_max"] == 0.15


def test_runtime_config_loads_extended_ocr_seed_defaults():
    from app.modules.importador.runtime_config import load_ocr_runtime_config

    invalidate_runtime_config_cache()

    config = load_ocr_runtime_config(None)

    assert config["pdf_render_dpi"] == 300
    assert config["image_contrast"] == 1.8
    assert config["image_sharpness"] == 2.0
    assert config["tesseract_languages"] == ["spa", "eng"]
    assert config["small_rotation_angles"] == ["-4", "-2", "2", "4"]
    assert config["threshold_value"] == 170
    assert config["threshold_low_value"] == 140
    assert config["perspective_threshold_value"] == 165
    assert config["easyocr_gpu"] is False
    assert config["excel_max_header_scan_rows"] == 25
    assert config["excel_max_preview_rows_per_sheet"] == 120
    assert config["excel_scan_rows_multiplier"] == 4
    assert config["excel_max_text_chars"] == 4000


def test_runtime_config_loads_routing_and_pattern_seed_defaults():
    invalidate_runtime_config_cache()

    categories = load_doc_categories_config(None)
    filename_cfg = load_filename_normalization_config(None)
    tax_id_cfg = load_tax_id_patterns_config(None)
    routing_aliases = load_routing_field_aliases(None)
    routing_labels = load_routing_field_labels(None)
    routing_profiles = load_routing_fallback_profiles_config(None)
    routing_rules = load_routing_fallback_rules_config(None)

    assert "invoice" in categories
    assert filename_cfg["uuid_patterns"]
    assert tax_id_cfg["match_patterns"]
    assert routing_aliases["vendor_tax_id"][:3] == ("vendor_tax_id", "supplier_tax_id", "ruc")
    assert routing_labels["vendor"] == "proveedor"
    assert routing_profiles["SUPPLIER_INVOICE"]["document_type"] == "supplier_invoice"
    assert any(rule["profile_code"] == "supplier_invoice" for rule in routing_rules)


def test_runtime_config_loads_extended_prompt_seed_defaults():
    invalidate_runtime_config_cache()

    config = load_prompt_config(None)

    assert config["vision_system_fallback"]
    assert config["structured_classification_task_preamble"]
    assert config["structured_classification_response_instruction"]
    assert config["structured_classification_preview_label"] == "Structured preview:"
    assert config["response_json_label"] == "Respond ONLY with valid JSON:"
    assert config["critical_rules_heading"] == "CRITICAL rules:"
    assert config["additional_instructions_heading"] == "Additional instructions:"
    assert "{current_year}" in config["year_sanity_rule_template"]
    assert "line_items" in config["line_items_extra_columns_rule"]


def test_pre_classifier_loader_delegates_to_runtime_config(monkeypatch):
    pre_classifier._cache.pop("config", None)

    delegated = {
        "min_header_confirmations": 5.0,
        "filename_min_confidence": 0.91,
        "header_coverage_min_ratio": 0.82,
        "structured_skip_threshold": 0.88,
        "ocr_weird_ratio_max": 0.09,
    }

    monkeypatch.setattr(
        "app.modules.importador.runtime_config.load_pre_classifier_runtime_config",
        lambda db=None: dict(delegated),
    )

    config = pre_classifier.load_pre_classifier_config(None)

    assert config == delegated


def test_pre_classifier_uses_runtime_filename_and_tax_id_config(monkeypatch):
    monkeypatch.setattr(
        "app.modules.importador.runtime_config.load_filename_normalization_config",
        lambda db=None: {
            "uuid_patterns": [r"customuuid"],
            "date_patterns": [],
            "long_number_patterns": [],
            "separator_patterns": [r"[_]+"],
        },
    )
    monkeypatch.setattr(
        "app.modules.importador.runtime_config.load_tax_id_patterns_config",
        lambda db=None: {
            "match_patterns": [r"VAT\s*:\s*([0-9]{9})"],
            "scan_max_chars": 200,
            "min_digits": 9,
            "max_digits": 9,
        },
    )

    assert pre_classifier._normalize_filename_stem("Factura_customuuid_abril.pdf") == "factura abril"
    assert pre_classifier._extract_ruc_from_text("Customer VAT: 123456789") == "123456789"
