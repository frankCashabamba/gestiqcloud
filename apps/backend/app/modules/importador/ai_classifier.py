"""Universal AI analyzer for any accounting document in any language."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import unicodedata
from typing import Any

from app.modules.importador.document_fields import safe_floatish
from app.modules.importador.ocr_quality import estimate_text_quality as _base_estimate_text_quality
from app.modules.importador.runtime_config import (
    _DEFAULT_OCR_CONFIG,
    load_ai_model_routing,
    load_ai_params,
    load_ai_runtime_config,
    load_doc_type_patterns,
    load_ocr_runtime_config,
    load_prompt_config,
    load_reprocess_control,
    load_tax_id_patterns_config,
)
from app.services.ai.base import AITask, model_name
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")


def _smart_content_sample(content: str, limit: int) -> str:
    """Muestrea el contenido en tres zonas: inicio, centro y final.

    En vez de truncar al inicio (content[:limit]), divide el límite en tercios
    para capturar cabecera del documento (vendor/fecha), cuerpo (line items)
    y pie (totales). Preserva el 100% si el contenido cabe en el límite.
    """
    if not content or len(content) <= limit:
        return content
    third = max(1, limit // 3)
    head = content[:third]
    mid_start = max(third, (len(content) - third) // 2)
    mid = content[mid_start : mid_start + third]
    tail = content[max(0, len(content) - third) :]
    return f"{head}\n[...]\n{mid}\n[...]\n{tail}"


def _resolve_model_for_doctype(doc_type: str | None, db: Any = None) -> str | None:
    """Retorna el nombre del modelo a usar para este doc_type según imp_config.

    Retorna None si no hay routing configurado (se usará el modelo por defecto
    del proveedor AI). Prioridad: doc_type específico > DEFAULT.
    """
    routing = load_ai_model_routing(db)
    if not routing:
        return None
    model = routing.get(str(doc_type or "").upper().strip()) or routing.get("DEFAULT") or ""
    return model if model else None


def _sanitize_extraction_model_override(model: str | None) -> str | None:
    resolved = model_name(model)
    if not resolved:
        return None
    if _is_non_extraction_model(resolved):
        logger.warning(
            "extraction_model_selection=blocked reason=no_allowed_extraction_model model=%s",
            resolved,
        )
        return None
    return resolved


def _is_non_extraction_model(model: str | None) -> bool:
    normalized = model_name(model).lower()
    if not normalized:
        return True

    base = normalized.split(":", 1)[0]
    blocked_prefixes = (
        "qwen2.5-coder",
        "qwen2.5",
        "minicpm-v",
        "llava",
        "bakllava",
        "moondream",
        "nomic-embed",
        "mxbai-embed",
        "snowflake-arctic-embed",
        "jina-embeddings",
        "all-minilm",
        "bge-",
        "gte-",
        "clip-",
    )
    if base.startswith(blocked_prefixes):
        return True

    blocked_tokens = (
        "vision",
        "multimodal",
        "embed",
        "embedding",
        "adapter",
        "proxy",
        "gateway",
        "openai",
        "azure",
        "anthropic",
        "bedrock",
        "vertex",
        "gemini",
    )
    return any(token in normalized for token in blocked_tokens)


def _build_document_time_context(prompt_config: dict[str, Any] | None, *, current_year: int) -> str:
    pc = prompt_config or load_prompt_config(None)
    template = str(
        pc.get("document_time_context_template")
        or "CONTEXT: Current year is {current_year}. Most documents are from {previous_year}-{current_year}."
    ).strip()
    return template.format(current_year=current_year, previous_year=current_year - 1)


def _estimate_text_quality(
    text: str,
    *,
    ai_runtime: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Estimate whether OCR text is good enough to avoid a vision pass."""
    return _base_estimate_text_quality(text, ai_runtime=ai_runtime)


def _should_use_vision_fallback(
    content: str,
    format_hint: str,
    image_bytes: bytes | None,
    *,
    ai_runtime: dict[str, Any] | None = None,
) -> bool:
    """Use vision only when OCR text is too weak and we have an image payload."""
    if not image_bytes:
        return False

    cfg = ai_runtime or load_ai_runtime_config(None)
    normalized_format = str(format_hint or "").strip().upper()
    allowed_formats = {
        str(item).strip().upper()
        for item in (cfg.get("vision_allowed_formats") or [])
        if str(item).strip()
    }
    if normalized_format not in allowed_formats:
        return False

    quality = _estimate_text_quality(content, ai_runtime=cfg)
    score = quality["score"]
    min_quality = max(0.0, min(1.0, float(cfg.get("ocr_min_quality") or 0.45)))
    min_words = max(1, int(cfg.get("ocr_min_words_for_vision") or 18))
    needs_vision = score < min_quality or quality["words"] < min_words

    logger.info(
        "OCR quality for %s: score=%.3f words=%s chars=%s threshold=%.2f vision=%s",
        normalized_format or "UNKNOWN",
        score,
        int(quality["words"]),
        int(quality["chars"]),
        min_quality,
        "yes" if needs_vision else "no",
    )
    return needs_vision


_CRITICAL_FIELD_NAMES: tuple[str, ...] = (
    "vendor",
    "customer",
    "doc_number",
    "invoice_number",
    "vendor_tax_id",
    "customer_tax_id",
    "issue_date",
    "currency",
    "subtotal",
    "tax_amount",
    "total_amount",
    "line_items",
)
_FIELD_REVIEW_THRESHOLD = 0.75


def _score_field_confidence(
    field_name: str,
    value: Any,
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any],
    ocr_runtime: dict[str, Any],
    analysis_path: str,
) -> float:
    from app.modules.importador.processing_service import _looks_like_noisy_scalar_text

    if value in (None, "", [], {}):
        return 0.0

    if analysis_path == "structured_direct":
        return 0.98

    normalized_content = _normalize_evidence_text(content)
    digits_content = _digits_only(content)
    quality = _estimate_text_quality(content, ai_runtime=ai_runtime)
    quality_factor = 0.65 + (0.35 * float(quality.get("score") or 0.0))
    confidence = 0.55
    normalized_format = str(format_hint or "").strip().upper()

    if field_name in {"vendor", "customer", "concept"}:
        confidence = 0.72
        if _value_token_evidence(normalized_content, value, ai_runtime=ai_runtime):
            confidence = 0.94
        elif _looks_like_noisy_scalar_text(str(value), field_name=field_name):
            confidence = 0.35
        elif normalized_format in {"IMAGE_OCR", "PDF_OCR"} and len(str(value).split()) > 1:
            confidence = 0.8
    elif field_name in {"doc_number", "invoice_number"}:
        confidence = 0.58
        if _value_token_evidence(normalized_content, value, min_len=3, ai_runtime=ai_runtime):
            confidence = 0.93
        elif _digits_only(value) and _digits_only(value) in digits_content:
            confidence = 0.9
    elif field_name in {"vendor_tax_id", "customer_tax_id"}:
        digits = _digits_only(value)
        confidence = 0.55
        if digits and len(digits) >= 10 and digits in digits_content:
            confidence = 0.96
        elif digits and len(digits) >= 10:
            confidence = 0.82
    elif field_name == "issue_date":
        confidence = 0.6
        if _value_token_evidence(normalized_content, value, min_len=4, ai_runtime=ai_runtime):
            confidence = 0.94
        elif _numeric_evidence(digits_content, value, min_len=6):
            confidence = 0.87
    elif field_name == "currency":
        confidence = 0.45
        if _currency_evidence(normalized_content, value, ai_runtime=ai_runtime):
            confidence = 0.96
    elif field_name in {"subtotal", "tax_amount", "total_amount"}:
        confidence = 0.62
        if _amount_has_monetary_context(
            content,
            value,
            field_name=field_name,
            ocr_runtime=ocr_runtime,
        ):
            confidence = 0.96
        elif _numeric_evidence(digits_content, value, min_len=3):
            confidence = 0.8
    elif field_name == "line_items":
        items = value if isinstance(value, list) else []
        confidence = 0.45 if not items else 0.72
        if items and _line_items_evidence(
            normalized_content,
            digits_content,
            items,
            ai_runtime=ai_runtime,
        ):
            confidence = 0.92
        elif items:
            confidence = max(confidence, 0.78 if len(items) >= 2 else 0.7)

    if normalized_format in {"IMAGE_OCR", "PDF_OCR"} and confidence < 1.0:
        confidence *= quality_factor
        if quality.get("repeat_ratio") and float(quality.get("repeat_ratio") or 0.0) > 0.35:
            confidence *= 0.88
        if float(quality.get("useful_hits") or 0.0) >= 2:
            confidence = min(1.0, confidence + 0.04)
    return max(0.0, min(1.0, confidence))


def _build_field_confidences(
    fields: dict[str, Any] | None,
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
    ocr_runtime: dict[str, Any] | None = None,
    analysis_path: str = "",
) -> dict[str, dict[str, Any]]:
    current_fields = fields if isinstance(fields, dict) else {}
    if not current_fields:
        return {}

    ai_cfg = ai_runtime or load_ai_runtime_config(None)
    ocr_cfg = ocr_runtime or load_ocr_runtime_config(None)
    result: dict[str, dict[str, Any]] = {}
    for field_name in _CRITICAL_FIELD_NAMES:
        value = current_fields.get(field_name)
        if value in (None, "", [], {}):
            continue
        confidence = _score_field_confidence(
            field_name,
            value,
            content=content,
            format_hint=format_hint,
            ai_runtime=ai_cfg,
            ocr_runtime=ocr_cfg,
            analysis_path=analysis_path,
        )
        result[field_name] = {"value": value, "confidence": round(confidence, 2)}

    for field_name, value in current_fields.items():
        if field_name in result or value in (None, "", [], {}) or str(field_name).startswith("_"):
            continue
        confidence = _score_field_confidence(
            str(field_name),
            value,
            content=content,
            format_hint=format_hint,
            ai_runtime=ai_cfg,
            ocr_runtime=ocr_cfg,
            analysis_path=analysis_path,
        )
        result[str(field_name)] = {"value": value, "confidence": round(confidence, 2)}
    return result


def _finalize_analysis_payload(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
    ocr_runtime: dict[str, Any] | None = None,
    analysis_path: str = "",
) -> dict[str, Any]:
    result = dict(parsed or {})
    fields = result.get("fields")
    if not isinstance(fields, dict):
        fields = {}
        result["fields"] = fields

    field_confidences = result.get("field_confidences")
    if not isinstance(field_confidences, dict) or not field_confidences:
        field_confidences = _build_field_confidences(
            fields,
            content=content,
            format_hint=format_hint,
            ai_runtime=ai_runtime,
            ocr_runtime=ocr_runtime,
            analysis_path=analysis_path or str(result.get("analysis_path") or ""),
        )
    result["field_confidences"] = field_confidences

    weak_fields = [
        field_name
        for field_name, payload in field_confidences.items()
        if isinstance(payload, dict)
        and payload.get("value") not in (None, "", [], {})
        and float(payload.get("confidence") or 0.0) < _FIELD_REVIEW_THRESHOLD
    ]
    if weak_fields or bool(result.get("requires_review")):
        result["requires_review"] = True
    return result


def _normalize_evidence_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9$€]+", " ", normalized)
    return " ".join(normalized.split())


def _value_token_evidence(
    text_normalized: str,
    value: Any,
    *,
    min_len: int = 4,
    ai_runtime: dict[str, Any] | None = None,
) -> bool:
    sample = _normalize_evidence_text(str(value or ""))
    if not sample:
        return False
    cfg = ai_runtime or load_ai_runtime_config(None)
    stop_tokens = {
        str(token).strip().lower()
        for token in (cfg.get("evidence_stop_tokens") or [])
        if str(token).strip()
    }
    tokens = [
        token for token in sample.split() if len(token) >= min_len and token not in stop_tokens
    ]
    if not tokens:
        return sample in text_normalized
    return any(token in text_normalized for token in tokens)


def _digits_only(value: Any) -> str:
    return re.sub(r"[^0-9]", "", str(value or ""))


def _numeric_evidence(text_digits: str, value: Any, *, min_len: int = 3) -> bool:
    digits = _digits_only(value)
    return bool(digits and len(digits) >= min_len and digits in text_digits)


def _amount_has_monetary_context(
    content: str,
    value: Any,
    *,
    field_name: str,
    ocr_runtime: dict[str, Any] | None = None,
) -> bool:
    amount = safe_floatish(value)
    if amount is None:
        return False

    cfg = ocr_runtime or load_ocr_runtime_config(None)
    total_cents = str(int(round(float(amount) * 100)))
    total_units = str(int(round(float(amount)))) if float(amount).is_integer() else None
    positive_patterns = _runtime_regex_patterns(
        cfg,
        f"{field_name}_positive_patterns",
        list(_DEFAULT_OCR_CONFIG.get(f"{field_name}_positive_patterns") or []),
    )
    reject_patterns = _runtime_regex_patterns(
        cfg,
        f"{field_name}_reject_patterns",
        list(_DEFAULT_OCR_CONFIG.get(f"{field_name}_reject_patterns") or []),
    )
    currency_tokens = _runtime_normalized_text_set(
        cfg,
        "money_currency_tokens",
        list(_DEFAULT_OCR_CONFIG["money_currency_tokens"]),
    )
    currency_symbols = {
        str(item).strip()
        for item in (
            cfg.get("money_currency_symbols") or _DEFAULT_OCR_CONFIG["money_currency_symbols"]
        )
        if str(item).strip()
    }

    for raw_line in str(content or "").splitlines():
        line = " ".join(str(raw_line or "").split()).strip()
        if not line:
            continue
        line_digits = _digits_only(line)
        if total_cents not in line_digits and (
            total_units is None or total_units not in line_digits
        ):
            continue
        normalized = _normalize_evidence_text(line)
        if any(pattern.search(normalized) for pattern in reject_patterns):
            continue
        if any(symbol in line for symbol in currency_symbols) or any(
            token in normalized for token in currency_tokens
        ):
            return True
        if any(pattern.search(normalized) for pattern in positive_patterns):
            return True

    return False


def _currency_evidence(
    text_normalized: str,
    value: Any,
    *,
    ai_runtime: dict[str, Any] | None = None,
) -> bool:
    raw = str(value or "").strip().upper()
    if not raw:
        return False
    cfg = ai_runtime or load_ai_runtime_config(None)
    currency_markers = cfg.get("currency_markers") or {}
    markers = currency_markers.get(raw, [raw.lower()])
    return any(marker in text_normalized for marker in markers)


def _line_items_evidence(
    text_normalized: str,
    text_digits: str,
    value: Any,
    *,
    ai_runtime: dict[str, Any] | None = None,
) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if not isinstance(item, dict):
            continue
        description = item.get("description")
        if description and _value_token_evidence(
            text_normalized,
            description,
            ai_runtime=ai_runtime,
        ):
            return True
        for key in ("quantity", "unit_price", "total_price"):
            if _numeric_evidence(text_digits, item.get(key)):
                return True
    return False


def _blank_low_evidence_fields(
    fields: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
) -> int:
    cfg = ai_runtime or load_ai_runtime_config(None)
    normalized_format = str(format_hint or "").strip().upper()
    evidence_formats = {
        str(item).strip().upper()
        for item in (cfg.get("ocr_evidence_formats") or [])
        if str(item).strip()
    }
    if normalized_format not in evidence_formats:
        return 0

    quality = _estimate_text_quality(content, ai_runtime=cfg)
    min_quality = max(0.0, min(1.0, float(cfg.get("ocr_min_quality") or 0.45)))
    min_words = max(1, int(cfg.get("ocr_min_words_for_vision") or 18))
    if quality["score"] >= min_quality and quality["words"] >= min_words:
        return 0

    text_normalized = _normalize_evidence_text(content)
    text_digits = _digits_only(content)
    cleared = 0

    evidence_checks: dict[str, Any] = {
        "vendor": lambda value: _value_token_evidence(text_normalized, value, ai_runtime=cfg),
        "vendor_tax_id": lambda value: _numeric_evidence(text_digits, value),
        "customer": lambda value: _value_token_evidence(text_normalized, value, ai_runtime=cfg),
        "customer_tax_id": lambda value: _numeric_evidence(text_digits, value),
        "doc_number": lambda value: (
            _value_token_evidence(text_normalized, value, min_len=3, ai_runtime=cfg)
            or _numeric_evidence(text_digits, value, min_len=5)
        ),
        "issue_date": lambda value: _numeric_evidence(text_digits, value),
        "currency": lambda value: _currency_evidence(text_normalized, value, ai_runtime=cfg),
        "payment_method": lambda value: _value_token_evidence(
            text_normalized, value, ai_runtime=cfg
        ),
        "payment_terms": lambda value: _value_token_evidence(
            text_normalized, value, ai_runtime=cfg
        ),
        "concept": lambda value: _value_token_evidence(text_normalized, value, ai_runtime=cfg),
        "subtotal": lambda value: _numeric_evidence(text_digits, value),
        "tax_amount": lambda value: _numeric_evidence(text_digits, value),
        "total_amount": lambda value: _numeric_evidence(text_digits, value),
        "line_items": lambda value: _line_items_evidence(
            text_normalized,
            text_digits,
            value,
            ai_runtime=cfg,
        ),
    }

    for field_name, checker in evidence_checks.items():
        if field_name not in fields:
            continue
        value = fields.get(field_name)
        if value in (None, "", []):
            continue
        if checker(value):
            continue
        fields[field_name] = [] if field_name == "line_items" else None
        cleared += 1

    return cleared


def _apply_low_evidence_guard(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
) -> None:
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return

    cfg = ai_runtime or load_ai_runtime_config(None)
    cleared = _blank_low_evidence_fields(
        fields,
        content=content,
        format_hint=format_hint,
        ai_runtime=cfg,
    )
    if cleared <= 0:
        return

    try:
        parsed["confidence"] = min(
            float(parsed.get("confidence") or 0.0),
            max(0.0, min(1.0, float(cfg.get("ocr_guard_confidence_cap") or 0.45))),
        )
    except (TypeError, ValueError):
        parsed["confidence"] = max(
            0.0, min(1.0, float(cfg.get("ocr_guard_confidence_cap") or 0.45))
        )

    reason = str(parsed.get("reasoning") or "").strip()
    guard_reason = str(
        cfg.get("low_evidence_reason_template")
        or "Low OCR evidence: cleared {cleared} unsupported field(s) to avoid hallucinated data."
    ).format(cleared=cleared)
    parsed["reasoning"] = f"{reason} {guard_reason}".strip() if reason else guard_reason


def _build_structured_classification_prompt(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None,
    prompt_config: dict[str, Any] | None = None,
) -> str:
    return _build_structured_classification_prompt_parts(
        content,
        filename,
        format_hint,
        recipe_config,
        prompt_config=prompt_config,
    )["full_prompt"]


def _build_structured_classification_prompt_parts(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None,
    prompt_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rc = recipe_config or {}
    pc = prompt_config or load_prompt_config(None)
    system_prefix = str(rc.get("prompt_system") or "").strip()
    task_preamble = str(
        pc.get("structured_classification_task_preamble")
        or (
            "Classify this structured accounting dataset.\n"
            "The content contains column headers and a few sample rows, not the full file."
        )
    ).strip()
    response_instruction = str(
        pc.get("structured_classification_response_instruction")
        or "Return ONLY valid JSON with keys: doc_type, confidence, reasoning."
    ).strip()
    preview_label = str(
        pc.get("structured_classification_preview_label") or "Structured preview:"
    ).strip()
    doc_type_instruction = str(
        pc.get("doc_type_instruction")
        or "Use concise uppercase labels such as INVOICE, RECEIPT, CREDIT_NOTE, "
        "BANK_STATEMENT, BANK_MOVEMENTS, INVENTORY, PRICE_LIST, COSTING, PAYROLL, OTHER."
    ).strip()
    current_year = datetime.datetime.now().year

    body = (
        f"{task_preamble}\n"
        f"{response_instruction}\n"
        f"File: {filename} | Format: {format_hint}\n"
        f"Current year: {current_year}\n\n"
        f"{preview_label}\n{content[:2500]}\n\n"
        f"{doc_type_instruction}"
    )

    full_prompt = system_prefix + "\n\n" + body if system_prefix else body
    return {
        "mode": "structured_classification",
        "full_prompt": full_prompt,
        "system_prompt": system_prefix,
        "user_prompt": body,
        "task_preamble": task_preamble,
        "response_instruction": response_instruction,
        "preview_label": preview_label,
        "doc_type_instruction": doc_type_instruction,
        "current_year": current_year,
    }


def _build_dynamic_fields_prompt(
    canonical_fields: dict[str, dict] | None,
    field_descriptions: dict[str, str] | None = None,
    prompt_config: dict[str, Any] | None = None,
) -> str:
    descriptions = field_descriptions or {}
    pc = prompt_config or load_prompt_config(None)
    if not canonical_fields:
        return str(pc.get("fallback_dynamic_fields_prompt") or "").rstrip()

    lines: list[str] = []
    for field_name in sorted(canonical_fields.keys()):
        meta = canonical_fields.get(field_name) or {}
        field_type = str(meta.get("type") or "text").strip().lower()
        custom_description = str(descriptions.get(field_name) or "").strip()
        if custom_description:
            rendered = f'"{custom_description}"'
        elif field_name == "line_items" or field_type == "list":
            rendered = '[{"description":"...","quantity":number,"unit_price":number,"total_price":number,"extra_columns":{"ColNameAsInDoc":"value"}}] or []'
        elif field_type == "numeric":
            rendered = "NUMBER or null"
        elif field_type == "date":
            rendered = '"YYYY-MM-DD or null"'
        elif field_type == "payment_method":
            rendered = '"payment method exactly as printed or null"'
        else:
            rendered = '"text/value as printed or null"'
        lines.append(f'    "{field_name}": {rendered}')
    return ",\n".join(lines)


def _build_json_response_contract(
    *,
    dynamic_fields_prompt: str,
    doc_type_instruction: str,
    is_table_literal: str,
    columns_literal: str,
    reasoning_hint: str,
) -> str:
    return (
        "{\n"
        f'  "doc_type": "{doc_type_instruction}",\n'
        '  "confidence": 0.0-1.0,\n'
        f'  "reasoning": "{reasoning_hint}",\n'
        f'  "is_table": {is_table_literal},\n'
        f'  "columns": {columns_literal},\n'
        '  "fields": {\n'
        f"{dynamic_fields_prompt}\n"
        "  }\n"
        "}"
    )


def _build_configured_rules(
    *,
    prompt_config: dict[str, Any] | None,
    current_year: int,
    vision_mode: bool = False,
) -> list[str]:
    pc = prompt_config or load_prompt_config(None)
    rules_key = "vision_critical_rules" if vision_mode else "critical_rules"
    configured_rules = [
        str(rule).strip() for rule in (pc.get(rules_key) or []) if str(rule).strip()
    ]
    if not configured_rules:
        configured_rules = [
            "The document may be in any language. Read it as-is and map to the configured canonical fields.",
            "total_amount must represent the grand total, not a quantity.",
            "vendor is the entity that issues or signs the document.",
            "If is_table=true, return columns and only visible summary values in fields.",
            "Extract payment_method and payment_terms when visible.",
            "Dates must use YYYY-MM-DD. Amounts must use dot decimal notation. Missing fields must be null.",
            "Do not invent data absent from the document.",
        ]
    year_rule_template = str(
        pc.get("year_sanity_rule_template")
        or "YEAR sanity check: we are in {current_year}. If you read '16' as year, it is almost certainly '{expected_year_suffix}' (20{expected_year_suffix})."
    ).strip()
    configured_rules.append(
        year_rule_template.format(
            current_year=current_year,
            expected_year_suffix=f"{current_year % 100:02d}",
        )
    )
    configured_rules.append(
        str(
            pc.get("line_items_extra_columns_rule")
            or (
                "line_items: only list actual PRODUCTS. "
                "For every visible line-item column that does not clearly map to the configured base fields, "
                "preserve it verbatim in extra_columns using the original header label and cell value. "
                "Do not drop visible line-item columns just because their meaning is uncertain."
            )
        ).strip()
    )
    return configured_rules


def _build_prompt_trace(
    *,
    mode: str,
    system_prompt: str,
    user_prompt: str,
    response_contract: str | None = None,
    critical_rules: list[str] | None = None,
    doc_type_instruction: str | None = None,
    learned_hints: str | None = None,
    custom_user_prompt: str | None = None,
    prompt_messages: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    full_prompt = system_prompt.rstrip() + "\n\n" + user_prompt if system_prompt else user_prompt
    trace: dict[str, Any] = {
        "mode": mode,
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "full_prompt": full_prompt,
    }
    if response_contract:
        trace["response_contract"] = response_contract
    if critical_rules is not None:
        trace["critical_rules"] = list(critical_rules)
    if doc_type_instruction:
        trace["doc_type_instruction"] = doc_type_instruction
    if learned_hints:
        trace["learned_hints"] = learned_hints
    if custom_user_prompt:
        trace["custom_user_prompt"] = custom_user_prompt
    if prompt_messages is not None:
        trace["messages"] = prompt_messages
    return trace


def _build_ai_fallback_policy_context(
    *,
    content: str,
    prompt_text: str,
    has_structured_rows: bool,
    image_bytes: bytes | None,
    ai_runtime: dict[str, Any],
    ai_params: dict[str, Any],
) -> dict[str, Any]:
    def _context_bool(key: str, default: bool) -> bool:
        value = ai_runtime.get(key, default)
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    quality = _estimate_text_quality(content, ai_runtime=ai_runtime)
    prompt_chars = len(prompt_text or "")
    content_chars = len(content or "")
    content_words = len(re.findall(r"\b\w+\b", str(content or ""), flags=re.UNICODE))
    content_lines = sum(1 for line in str(content or "").splitlines() if line.strip())

    prompt_threshold = max(1, int(ai_runtime.get("openai_fallback_prompt_chars_threshold") or 7000))
    content_threshold = max(
        1,
        int(
            ai_runtime.get("openai_fallback_content_chars_threshold")
            or ai_params.get("content_limit_unstructured")
            or (4000 if has_structured_rows else 7000)
        ),
    )
    word_threshold = max(
        1,
        int(
            ai_runtime.get("openai_fallback_word_count_threshold")
            or (220 if has_structured_rows else 120)
        ),
    )
    line_threshold = max(1, int(ai_runtime.get("openai_fallback_line_count_threshold") or 30))
    quality_threshold = float(ai_runtime.get("openai_fallback_ocr_quality_threshold") or 0.45)
    complexity_threshold = float(ai_runtime.get("openai_fallback_complexity_threshold") or 0.72)
    slow_threshold_ms = int(ai_runtime.get("openai_fallback_slow_threshold_ms") or 15000)

    prompt_ratio = min(prompt_chars / prompt_threshold, 1.5)
    content_ratio = min(content_chars / content_threshold, 1.5)
    word_ratio = min(content_words / word_threshold, 1.5)
    row_ratio = min(content_lines / line_threshold, 1.5) if has_structured_rows else 0.0
    quality_gap = max(0.0, 1.0 - float(quality["score"]))
    image_bonus = 0.05 if image_bytes else 0.0

    complexity_score = min(
        1.0,
        round(
            (0.30 * prompt_ratio)
            + (0.25 * content_ratio)
            + (0.15 * word_ratio)
            + (0.20 * quality_gap)
            + (0.10 * row_ratio)
            + image_bonus,
            3,
        ),
    )

    reasons: list[str] = []
    if prompt_chars >= prompt_threshold:
        reasons.append(f"prompt_chars>={prompt_threshold}")
    if content_chars >= content_threshold:
        reasons.append(f"content_chars>={content_threshold}")
    if content_words >= word_threshold:
        reasons.append(f"content_words>={word_threshold}")
    if has_structured_rows and content_lines >= line_threshold:
        reasons.append(f"structured_rows>={line_threshold}")
    if quality["score"] <= quality_threshold:
        reasons.append(f"ocr_quality<={quality_threshold:.2f}")
    if image_bytes:
        reasons.append("image_payload")

    return {
        "ai_fallback_policy": {
            "enabled": True,
            "allow_on_error": _context_bool("openai_fallback_on_error", False),
            "allow_on_slow": True,
            "allow_on_complex": True,
            "complexity_score": complexity_score,
            "complexity_threshold": complexity_threshold,
            "slow_threshold_ms": slow_threshold_ms,
            "prompt_chars": prompt_chars,
            "prompt_chars_threshold": prompt_threshold,
            "content_chars": content_chars,
            "content_chars_threshold": content_threshold,
            "content_words": content_words,
            "content_words_threshold": word_threshold,
            "ocr_quality": round(float(quality["score"]), 3),
            "ocr_quality_threshold": quality_threshold,
            "structured_rows": content_lines if has_structured_rows else None,
            "structured_rows_threshold": line_threshold if has_structured_rows else None,
            "reasons": reasons,
        }
    }


async def _analyze_structured_document(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    prompt_config: dict[str, Any] | None = None,
    db: Any = None,
    *,
    bypass_cache: bool = False,
    provider_override: str | None = None,
) -> dict[str, Any]:
    """Cheap classification path for already structured datasets."""
    prompt_parts = _build_structured_classification_prompt_parts(
        content,
        filename,
        format_hint,
        recipe_config,
        prompt_config=prompt_config,
    )
    prompt = str(prompt_parts["full_prompt"])

    ai_params = load_ai_params(db)
    temperature = float(ai_params.get("temperature") or 0.1)
    max_tokens = int(ai_params.get("max_tokens_classification") or 220)
    model_override = _resolve_model_for_doctype(None, db)  # sin doc_type aún, usa DEFAULT
    ai_runtime = load_ai_runtime_config(db)
    fallback_context = _build_ai_fallback_policy_context(
        content=content,
        prompt_text=prompt,
        has_structured_rows=True,
        image_bytes=None,
        ai_runtime=ai_runtime,
        ai_params=ai_params,
    )

    def _structured_fallback(
        *,
        raw_response: Any,
        model_used_value: str,
        analysis_path: str,
        cache_hit: bool,
    ) -> dict[str, Any]:
        """Construye un resultado de fallback para clasificacion estructurada."""
        fb = _fallback_classify(content, filename, fallback_patterns)
        fb.update({"is_table": True, "columns": [], "fields": {}})
        fb["raw_response"] = raw_response
        fb["model_used"] = model_used_value
        fb["prompt_full"] = prompt
        fb["prompt_parts"] = prompt_parts
        fb["analysis_path"] = analysis_path
        fb["cache_hit"] = cache_hit
        fb["cache_bypassed"] = bool(bypass_cache)
        return fb

    try:
        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            context=fallback_context,
            module="importador",
            enable_recovery=True,
            model=model_override,
            provider=provider_override,
            bypass_cache=bypass_cache,
        )
        raw_content = response.content
        model_used = response.model or "unknown"
        response_metadata = getattr(response, "metadata", None) or {}
        cache_hit_flag = bool(response_metadata.get("source") == "redis_cache")

        if response.is_error:
            return _structured_fallback(
                raw_response=response.error,
                model_used_value=model_used,
                analysis_path="fallback",
                cache_hit=cache_hit_flag,
            )

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
            parsed["is_table"] = True
            parsed["columns"] = []
            parsed["fields"] = {}
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_full"] = prompt
            parsed["prompt_parts"] = prompt_parts
            parsed["analysis_path"] = "ai_structured"
            parsed["cache_hit"] = cache_hit_flag
            parsed["cache_bypassed"] = bool(bypass_cache)
            return parsed

        return _structured_fallback(
            raw_response=raw_content,
            model_used_value=model_used,
            analysis_path="fallback",
            cache_hit=cache_hit_flag,
        )
    except Exception as exc:
        logger.error("Structured AI analysis error: %s", exc)
        return _structured_fallback(
            raw_response=str(exc),
            model_used_value="fallback",
            analysis_path="fallback_error",
            cache_hit=False,
        )


def _clean_vision_fields(fields: dict) -> None:
    """Post-process vision model output to fix common mistakes in-place."""
    for key in ("total_amount", "subtotal", "tax_amount"):
        val = fields.get(key)
        if isinstance(val, str):
            cleaned = val.replace(",", "").replace(" ", "").strip()
            try:
                fields[key] = float(cleaned)
            except (ValueError, TypeError):
                pass

    for key in ("vendor_tax_id", "customer_tax_id"):
        val = fields.get(key)
        if isinstance(val, str):
            fields[key] = re.sub(r"[^0-9]", "", val) or None

    date_val = fields.get("issue_date")
    if isinstance(date_val, str):
        if "T" in date_val:
            date_val = date_val.split("T")[0]
        date_val = date_val.strip()[:10]
        fields["issue_date"] = date_val if re.match(r"^\d{4}-\d{2}-\d{2}$", date_val) else date_val

    items = fields.get("line_items")
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            for k in ("quantity", "unit_price", "total_price"):
                v = item.get(k)
                if isinstance(v, str):
                    try:
                        item[k] = float(v.replace(",", "").strip())
                    except (ValueError, TypeError):
                        pass

    for key in ("payment_method", "payment_terms"):
        val = fields.get(key)
        if isinstance(val, str):
            cleaned = re.sub(
                r"^(payment\s*(method|type|terms?)|metodo\s+de\s+pago|forma\s+de\s+pago|tipo\s+de\s+pago)\s*[:\-]\s*",
                "",
                val.strip(),
                flags=re.IGNORECASE,
            )
            fields[key] = cleaned or val.strip()


def _parse_amount_token(token: str) -> float | None:
    cleaned = str(token or "").strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned)
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def _extract_amount_candidates_from_line(line: str) -> list[float]:
    candidates: list[float] = []

    combined_matches = list(re.finditer(r"(?<![\d,.])(\d{1,6})\s+(\d{2})(?![\d,.])", line))
    combined_spans = [match.span() for match in combined_matches]
    for match in combined_matches:
        start, end = match.span()
        if (start > 0 and line[start - 1] == "%") or (
            end < len(line) and line[end : end + 1] == "%"
        ):
            continue
        amount = _parse_amount_token(f"{match.group(1)}.{match.group(2)}")
        if amount is not None:
            candidates.append(amount)

    decimal_like_matches = list(
        re.finditer(r"(?<![\d,.])(?:\d{1,3}(?:[.,]\d{3})+|\d{1,6})(?:[.,]\d{2})?(?![\d,.])", line)
    )
    for match in decimal_like_matches:
        start, end = match.span()
        if any(start >= c_start and end <= c_end for c_start, c_end in combined_spans):
            continue
        if (start > 0 and line[start - 1] == "%") or (
            end < len(line) and line[end : end + 1] == "%"
        ):
            continue
        amount = _parse_amount_token(match.group(0))
        if amount is not None:
            candidates.append(amount)

    return candidates


def _looks_like_date_context(line: str) -> bool:
    normalized = str(line or "").lower()
    if not normalized:
        return False
    if re.search(r"\b20\d{2}[-/]\d{2}[-/]\d{2}", normalized):
        return True
    if re.search(r"\b\d{1,2}[:/]\d{2}(:\d{2})?", normalized):
        return True
    if "fecha" in normalized or "emision" in normalized or "autorizacion" in normalized:
        if re.search(r"\b20\d{2}\b", normalized):
            return True
    return False


def _extract_money_like_amounts_from_line(line: str) -> list[float]:
    candidates: list[float] = []
    combined_matches = list(re.finditer(r"(?<![\d,.])(\d{1,6})\s+(\d{2})(?![\d,.])", line))
    for match in combined_matches:
        start, end = match.span()
        if (start > 0 and line[start - 1] == "%") or (
            end < len(line) and line[end : end + 1] == "%"
        ):
            continue
        amount = _parse_amount_token(f"{match.group(1)}.{match.group(2)}")
        if amount is not None:
            candidates.append(amount)

    decimal_matches = list(
        re.finditer(r"(?<![\d,.])\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?(?![\d,.])", line)
    )
    decimal_matches.extend(list(re.finditer(r"(?<![\d,.])\d+[.,]\d{2}(?![\d,.])", line)))
    for match in decimal_matches:
        start, end = match.span()
        if (start > 0 and line[start - 1] == "%") or (
            end < len(line) and line[end : end + 1] == "%"
        ):
            continue
        amount = _parse_amount_token(match.group(0))
        if amount is not None:
            candidates.append(amount)
    return candidates


def _amount_labels(prompt_config: dict[str, Any] | None = None) -> dict[str, tuple[str, ...]]:
    configured = (prompt_config or {}).get("amount_labels")
    if not isinstance(configured, dict):
        try:
            from .runtime_config import load_amount_label_config

            configured = load_amount_label_config(None)
        except Exception:
            configured = {}
    if not isinstance(configured, dict):
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for field_name, values in configured.items():
        if not isinstance(values, list):
            continue
        cleaned = tuple(str(value).strip().lower() for value in values if str(value).strip())
        if cleaned:
            result[str(field_name).strip()] = cleaned
    return result


def _extract_labeled_amount(
    content: str,
    field_name: str,
    *,
    prompt_config: dict[str, Any] | None = None,
) -> float | None:
    cfg = load_ocr_runtime_config(None)
    labels = _amount_labels(prompt_config).get(field_name) or ()
    if not labels:
        return None

    candidates: list[float] = []
    reject_total_patterns = _runtime_regex_patterns(
        cfg,
        "total_amount_reject_patterns",
        list(_DEFAULT_OCR_CONFIG["total_amount_reject_patterns"]),
    )
    tax_amount_lookahead_required_tokens = _runtime_normalized_text_set(
        cfg,
        "tax_amount_lookahead_required_tokens",
        list(_DEFAULT_OCR_CONFIG["tax_amount_lookahead_required_tokens"]),
    )
    amount_lookahead_reject_tokens = _runtime_normalized_text_set(
        cfg,
        "amount_lookahead_reject_tokens",
        list(_DEFAULT_OCR_CONFIG["amount_lookahead_reject_tokens"]),
    )
    label_patterns = [(label, re.compile(rf"\b{re.escape(label)}\b")) for label in labels]
    lines = [str(line).strip() for line in str(content or "").splitlines()]
    for idx, raw_line in enumerate(lines):
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        line_lower = line.lower()
        match_info = next(
            (
                (label, pattern.search(line_lower))
                for label, pattern in label_patterns
                if pattern.search(line_lower)
            ),
            None,
        )
        if match_info is None:
            continue
        matched_label, matched = match_info
        assert matched is not None
        if field_name == "total_amount" and any(
            pattern.search(line_lower) for pattern in reject_total_patterns
        ):
            continue
        if field_name == "total_amount" and matched_label == "total" and "%" in line_lower:
            continue

        segment = line[matched.end() :].strip() or line
        amount_candidates = _extract_amount_candidates_from_line(segment)
        if not amount_candidates:
            for lookahead in lines[idx + 1 : min(len(lines), idx + 3)]:
                lookahead = " ".join(str(lookahead).split()).strip()
                if not lookahead:
                    continue
                if _looks_like_date_context(lookahead):
                    continue
                lookahead_lower = _normalize_evidence_text(lookahead)
                if field_name == "tax_amount" and not any(
                    token in lookahead_lower for token in tax_amount_lookahead_required_tokens
                ):
                    continue
                if any(token in lookahead_lower for token in amount_lookahead_reject_tokens):
                    continue
                amount_candidates = _extract_amount_candidates_from_line(lookahead)
                if amount_candidates:
                    break
        for amount in reversed(amount_candidates):
            if (
                field_name == "tax_amount"
                and float(amount).is_integer()
                and 1900 <= float(amount) <= 2100
            ):
                continue
            candidates.append(amount)
            break

    if not candidates:
        return None
    if field_name == "subtotal":
        return max(candidates)
    return candidates[-1]


def _extract_contextual_max_amount(content: str) -> float | None:
    keywords = (
        re.compile(r"\bvalor\s+total\b"),
        re.compile(r"\bimporte\s+total\b"),
        re.compile(r"\bmonto\s+total\b"),
        re.compile(r"\bimporte\s+moneda\b"),
        re.compile(r"\btotal\b"),
        re.compile(r"\bimporte\b"),
        re.compile(r"\bmonto\b"),
        re.compile(r"\btarjeta\b"),
        re.compile(r"\befectivo\b"),
        re.compile(r"\bcambio\b"),
    )
    reject_total_patterns = (
        re.compile(r"\bsubtotal\b"),
        re.compile(r"\bsub total\b"),
        re.compile(r"\biva\b"),
        re.compile(r"\bvat\b"),
        re.compile(r"\bigv\b"),
        re.compile(r"\bimpuesto\b"),
        re.compile(r"\bnum(?:ero)?\s+total\s+art"),
        re.compile(r"\bart(?:\.|iculos?)?\s+vendid"),
        re.compile(r"\btotal\s+art"),
        re.compile(r"\bnumero\s+operacion\b"),
        re.compile(r"\bnumero\s+autorizacion\b"),
        re.compile(r"\bnumero\s+tarjeta\b"),
        re.compile(r"\bcodigo\s+respuesta\b"),
        re.compile(r"\breferencia\b"),
        re.compile(r"\baid\b"),
        re.compile(r"\bverificacion\s+usuario\b"),
    )
    candidates: list[float] = []
    for raw_line in str(content or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        line_lower = line.lower()
        if not any(pattern.search(line_lower) for pattern in keywords):
            continue
        if any(pattern.search(line_lower) for pattern in reject_total_patterns):
            continue
        for amount in _extract_money_like_amounts_from_line(line):
            if amount > 0:
                candidates.append(round(amount, 2))

    if not candidates:
        return None
    return max(candidates)


def _extract_issue_date_from_ocr(content: str) -> str | None:
    text = str(content or "")
    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})(?:[T\s]|$)", text)
    if iso_match:
        return f"{iso_match.group(1)}-{iso_match.group(2)}-{iso_match.group(3)}"

    slash_match = re.search(r"\b(\d{2})[/-](\d{2})[/-](20\d{2})\b", text)
    if slash_match:
        first = int(slash_match.group(1))
        second = int(slash_match.group(2))
        year = int(slash_match.group(3))
        if first > 12 and second <= 12:
            day, month = first, second
        elif second > 12 and first <= 12:
            day, month = second, first
        else:
            day, month = first, second
        return f"{year:04d}-{month:02d}-{day:02d}"

    ymd_match = re.search(r"\b(20\d{2})[/-](\d{2})[/-](\d{2})\b", text)
    if ymd_match:
        return f"{ymd_match.group(1)}-{ymd_match.group(2)}-{ymd_match.group(3)}"

    normalized = _normalize_evidence_text(text)
    written_match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(20\d{2})\b",
        normalized,
    )
    if not written_match:
        return None
    ai_runtime = load_ai_runtime_config(None)
    month_map = ai_runtime.get("ocr_written_months") or {}
    month = month_map.get(written_match.group(2))
    if month is None:
        return None
    day = int(written_match.group(1))
    year = int(written_match.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_tax_id_from_ocr(content: str) -> str | None:
    text = str(content or "")
    if not text:
        return None

    try:
        cfg = load_tax_id_patterns_config(None)
    except Exception:
        cfg = {
            "match_patterns": [
                r"(?:R\.?U\.?C\.?|RUC|NIF|CIF|CUIT|CUIL|RFC)\s*[:\-#]?\s*([0-9][\d\-]{6,19})",
                r"\b(20\d{9}|10\d{9})\b",
            ],
            "scan_max_chars": 3000,
            "min_digits": 8,
            "max_digits": 15,
        }

    patterns = [
        str(pattern) for pattern in (cfg.get("match_patterns") or []) if str(pattern).strip()
    ]
    scan_max_chars = int(cfg.get("scan_max_chars") or 3000)
    min_digits = int(cfg.get("min_digits") or 8)
    max_digits = int(cfg.get("max_digits") or 15)

    for pattern in patterns:
        match = re.search(pattern, text[:scan_max_chars], re.IGNORECASE)
        if not match:
            continue
        groups = (
            [match.group(i) for i in range(1, (match.lastindex or 0) + 1)]
            if match.lastindex
            else []
        )
        candidates = groups or [match.group(0)]
        for candidate in candidates:
            digits = _digits_only(candidate)
            if min_digits <= len(digits) <= max_digits:
                return digits
    return None


def _normalize_invoice_ocr_line(
    line: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> str:
    text = str(line or "").replace("\xa0", " ")
    cfg = ocr_runtime or load_ocr_runtime_config(None)
    cleanup_patterns = [
        str(pattern).strip()
        for pattern in (cfg.get("line_cleanup_patterns") or [])
        if str(pattern).strip()
    ]
    for pattern in cleanup_patterns:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _runtime_normalized_text_set(
    cfg: dict[str, Any],
    key: str,
    defaults: list[str],
) -> set[str]:
    values = cfg.get(key) or defaults
    return {_normalize_evidence_text(value) for value in values if str(value).strip()}


def _runtime_regex_patterns(
    cfg: dict[str, Any],
    key: str,
    defaults: list[str],
    *,
    flags: int = 0,
) -> list[re.Pattern[str]]:
    patterns = cfg.get(key) or defaults
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        raw = str(pattern or "").strip()
        if not raw:
            continue
        try:
            compiled.append(re.compile(raw, flags))
        except re.error as exc:
            logger.warning("Ignoring invalid OCR regex for %s: %s (%s)", key, raw, exc)
    return compiled


def _normalize_invoice_description(description: str, *, text_normalized: str) -> str | None:
    cleaned = " ".join(str(description or "").split()).strip(" -–—|/.,;:()[]{}")
    if not cleaned:
        return None

    candidate = cleaned
    tokens = candidate.split()
    if not tokens:
        return None

    first = tokens[0].strip(" -–—|/.,;:()[]{}")
    variants = [first]
    if len(first) > 4:
        variants.extend(
            [
                first[1:],
                first.lstrip("Ii"),
                first[1:].lstrip("Ii"),
            ]
        )

    for variant in variants:
        variant = variant.strip(" -–—|/.,;:()[]{}")
        if len(variant) < 3:
            continue
        rebuilt = " ".join([variant, *tokens[1:]]).strip()
        rebuilt_normalized = _normalize_evidence_text(rebuilt)
        if rebuilt_normalized and rebuilt_normalized in text_normalized:
            return rebuilt

    if len(tokens) > 1:
        rebuilt = " ".join(tokens[1:]).strip()
        rebuilt_normalized = _normalize_evidence_text(rebuilt)
        if rebuilt_normalized and rebuilt_normalized in text_normalized:
            return rebuilt

    first_token = tokens[0].strip(" -–—|/.,;:()[]{}")
    if len(first_token) > 4 and first_token[:1].lower() == "i" and first_token[1:].isalpha():
        rebuilt = " ".join([first_token[1:], *tokens[1:]]).strip()
        return rebuilt

    candidate_normalized = _normalize_evidence_text(candidate)
    if candidate_normalized and candidate_normalized in text_normalized:
        return candidate

    return candidate


def _normalize_invoice_description_strict(description: str) -> str | None:
    cleaned = " ".join(str(description or "").split()).strip(" -_/.,;:()[]{}")
    if not cleaned:
        return None
    tokens = cleaned.split()
    if not tokens:
        return None
    first = tokens[0].strip(" -_/.,;:()[]{}")
    if len(first) > 4 and first[:1].lower() == "i" and first[1:].isalpha():
        return " ".join([first[1:], *tokens[1:]]).strip()
    return cleaned


def _extract_invoice_doc_number_from_ocr(
    content: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> str | None:
    text = str(content or "")
    if not text:
        return None

    lines = [str(line).strip() for line in text.splitlines() if str(line).strip()]
    keyword_patterns = [
        re.compile(
            r"\b(?:factura|invoice|boleta|nota de venta|comprobante|documento|n[úu]m(?:ero|ero)|numero|nro\.?|no\.?)\b"
            r"[^\w]{0,20}"
            r"((?:\d{3}\s*[-/ ]\s*){2}\d{3,15}|[A-Z]{1,8}[-/]?\d{3,}[-/]?\d*)",
            re.IGNORECASE,
        ),
        re.compile(r"\b(\d{3}\s*[-/ ]\s*\d{3}\s*[-/ ]\s*\d{6,})\b"),
    ]

    cfg = ocr_runtime or load_ocr_runtime_config(None)
    keyword_patterns = _runtime_regex_patterns(
        cfg,
        "invoice_doc_number_keyword_patterns",
        list(_DEFAULT_OCR_CONFIG["invoice_doc_number_keyword_patterns"]),
        flags=re.IGNORECASE,
    )
    context_tokens = _runtime_normalized_text_set(
        cfg,
        "invoice_doc_number_context_tokens",
        list(_DEFAULT_OCR_CONFIG["invoice_doc_number_context_tokens"]),
    )

    for line in lines[:20]:
        normalized_line = _normalize_invoice_ocr_line(line, ocr_runtime=ocr_runtime)
        if not normalized_line:
            continue
        normalized_line_norm = _normalize_evidence_text(normalized_line)
        if not any(token in normalized_line_norm for token in context_tokens):
            continue
        for pattern in keyword_patterns:
            match = pattern.search(normalized_line)
            if not match:
                continue
            candidate = str(match.group(1) or "").strip()
            if not candidate:
                continue
            candidate = re.sub(r"\s*[-/ ]\s*", "-", candidate)
            candidate = re.sub(r"-{2,}", "-", candidate).strip("-")
            if len(candidate) >= 6:
                return candidate

    fallback_patterns = [
        re.compile(r"\b(\d{3}[-/]\d{3}[-/]\d{6,})\b"),
        re.compile(r"\b(\d{3}\s*[-/ ]?\s*\d{3}\s*[-/ ]?\s*\d{6,})\b"),
        re.compile(r"\b([A-Z]{1,8}[-/]\d{3,}[-/]\d{3,})\b"),
    ]
    fallback_patterns = _runtime_regex_patterns(
        cfg,
        "invoice_doc_number_fallback_patterns",
        list(_DEFAULT_OCR_CONFIG["invoice_doc_number_fallback_patterns"]),
    )
    for pattern in fallback_patterns:
        match = pattern.search(text)
        if match:
            candidate = str(match.group(1) or "").strip()
            candidate = re.sub(r"\s*[-/ ]\s*", "-", candidate)
            candidate = re.sub(r"-{2,}", "-", candidate).strip("-")
            digits = _digits_only(candidate)
            if len(digits) >= 12 and digits.startswith("001001"):
                candidate = f"001-001-{digits[6:]}"
            if len(candidate) >= 6:
                return candidate
    return None


def _extract_vendor_name_from_ocr(
    content: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> str | None:
    text = str(content or "")
    if not text:
        return None

    lines = [str(line).strip() for line in text.splitlines() if str(line).strip()]
    if not lines:
        return None

    stop_norms = {
        "datos del cliente",
        "razon social",
        "razon social / nombres y apellidos",
        "nombres y apellidos",
        "cliente",
        "vendedor",
        "ruc",
        "c.i",
        "direccion",
        "telefono",
        "email",
        "correo",
        "forma de pago",
        "fecha de emision",
        "fecha vencimiento",
        "subtotal",
        "total",
        "iva",
        "descuentos",
        "ambiente",
        "emision",
        "autorizacion",
        "producto",
    }
    cfg = ocr_runtime or load_ocr_runtime_config(None)
    stop_norms = _runtime_normalized_text_set(
        cfg,
        "invoice_vendor_stop_tokens",
        list(_DEFAULT_OCR_CONFIG["invoice_vendor_stop_tokens"]),
    )
    suffix_patterns = _runtime_regex_patterns(
        cfg,
        "invoice_vendor_suffix_patterns",
        list(_DEFAULT_OCR_CONFIG["invoice_vendor_suffix_patterns"]),
        flags=re.IGNORECASE,
    )
    ruc_index = next(
        (
            idx
            for idx, line in enumerate(lines[:20])
            if re.search(r"\b(?:ruc|nit|cif|rfc)\b", _normalize_evidence_text(line))
        ),
        None,
    )

    search_limit = min(len(lines), (ruc_index if ruc_index is not None else 10) + 2)
    candidates: list[tuple[float, str]] = []
    for idx, line in enumerate(lines[:search_limit]):
        clean = _normalize_invoice_ocr_line(line, ocr_runtime=cfg)
        if not clean:
            continue
        prefix = re.split(r"\d", clean, 1)[0].strip(" ,;:-")
        working = (
            prefix
            if prefix and any(pattern.search(prefix) for pattern in suffix_patterns)
            else clean
        )
        normalized = _normalize_evidence_text(working)
        if any(stop in normalized for stop in stop_norms):
            continue
        if (
            ("factura" in normalized and ("simplificada" in normalized or "simplif" in normalized))
            or "ticket" in normalized
            or "para el cliente" in normalized
        ):
            continue
        if normalized.startswith("establecimiento") or normalized.startswith("localidad"):
            continue

        alpha_words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}", working)
        if len(alpha_words) < 2:
            continue
        if sum(1 for ch in working if ch.isdigit()) > 3 and not any(
            pattern.search(working) for pattern in suffix_patterns
        ):
            continue

        score = float(len(alpha_words))
        if any(pattern.search(working) for pattern in suffix_patterns):
            score += 6.0
        if working.upper() == working:
            score += 1.5
        if ruc_index is not None and idx == max(0, ruc_index - 1):
            score += 3.0
        if idx <= 3:
            score += 1.0
        if "cliente" in normalized:
            score -= 4.0
        candidates.append((score, working))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


# Patrón POS ticket: "1.00x descripcion $2.50" o "10x tapados $1.50"
_POS_ITEM_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*[xX×]\s+(.+?)\s+\$\s*(\d+(?:[.,]\d+)?)\s*$")
# Línea que contiene SOLO un número o importe (para detectar filas multi-línea)
_STANDALONE_AMOUNT_RE = re.compile(r"^\$?\s*\d+(?:[.,]\d{1,3})?\s*$")


def _extract_pos_ticket_items_from_ocr(text: str) -> list[dict[str, Any]]:
    """Extrae items de tickets POS con formato '1.00x descripcion $precio'."""
    items: list[dict[str, Any]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        m = _POS_ITEM_RE.match(line)
        if not m:
            continue
        qty_str = m.group(1)
        desc = m.group(2).strip().rstrip(".").strip()
        price_str = m.group(3)
        qty = safe_floatish(qty_str) or 1.0
        price = safe_floatish(price_str) or 0.0
        if not desc or len(desc) < 2 or price <= 0:
            continue
        unit_price = round(price / qty, 6) if qty else price
        items.append(
            {
                "description": desc,
                "quantity": qty,
                "unit_price": unit_price,
                "total_price": price,
            }
        )
    return items


def _join_multiline_table_rows(lines: list[str]) -> list[str]:
    """Colapsa filas de tabla donde descripción y valores están en líneas separadas.

    Detecta el patrón típico de facturas PDF que exportan cada celda en su
    propia línea (descripción → qty → precio_unitario → total) y las une
    en una sola línea para que el extractor principal las procese.

    Ejemplo Render invoice:
        "Servers - 743h 59m 59s - 1 instance"  →  línea de descripción
        "1"                                      →  qty solo
        "$7.00"                                  →  precio unitario solo
        "$7.00"                                  →  total solo
    Se une en: "Servers - 743h 59m 59s - 1 instance 1 7.00 7.00"
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Solo intentar colapsar si la línea actual NO es ella misma un número suelto
        if not _STANDALONE_AMOUNT_RE.match(line.strip()):
            j = i + 1
            joined_count = 0
            while j < len(lines) and joined_count < 3:
                next_stripped = lines[j].strip()
                if _STANDALONE_AMOUNT_RE.match(next_stripped):
                    joined_count += 1
                    j += 1
                else:
                    break
            # Colapsar solo si hay al menos 2 valores numéricos seguidos (qty + precio/s)
            if joined_count >= 2:
                parts = [line] + [lines[k].strip() for k in range(i + 1, j)]
                result.append(" ".join(parts))
                i = j
                continue
        result.append(line)
        i += 1
    return result


def _join_visual_invoice_amount_rows(lines: list[str]) -> list[str]:
    """Join photographed invoice rows where the total wrapped to the next line."""
    result: list[str] = []
    i = 0
    while i < len(lines):
        line = str(lines[i] or "").strip()
        if not line:
            i += 1
            continue
        if i + 1 < len(lines):
            next_line = str(lines[i + 1] or "").strip()
            current_amounts = _extract_money_like_amounts_from_line(line)
            next_amounts = _extract_money_like_amounts_from_line(next_line)
            normalized = _normalize_evidence_text(line)
            if (
                len(current_amounts) >= 2
                and len(next_amounts) == 1
                and next_line.count(" ") <= 1
                and not any(
                    marker in normalized
                    for marker in (
                        "subtotal",
                        "sub total",
                        "total",
                        "iva",
                        "fecha",
                        "ruc",
                        "razon social",
                        "nombres y apellidos",
                    )
                )
            ):
                result.append(f"{line} {next_line}")
                i += 2
                continue
        result.append(line)
        i += 1
    return result


def _token_looks_like_invoice_code(token: str) -> bool:
    raw = str(token or "").strip()
    if not raw:
        return True
    digits = _digits_only(raw)
    if len(digits) > 8:
        return True
    if re.search(r"[A-Za-z]", raw) and re.search(r"\d", raw):
        return True
    if "-" in raw and re.search(r"[A-Za-z]", raw):
        return True
    return False


def _extract_invoice_line_items_from_ocr(
    content: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    text = str(content or "")
    if not text:
        return []

    text_normalized = _normalize_evidence_text(text)
    # Pre-procesar: colapsar filas multi-línea antes del análisis token a token
    raw_lines = [str(line).strip() for line in text.splitlines() if str(line).strip()]
    lines = _join_visual_invoice_amount_rows(_join_multiline_table_rows(raw_lines))
    if not lines:
        return []

    skip_markers = {
        "subtotal",
        "subtotal sin impuestos",
        "sub total",
        "iva",
        "descuento",
        "total",
        "fecha",
        "ruc",
        "cliente",
        "vendedor",
        "direccion",
        "telefono",
        "email",
        "forma de pago",
        "entregar",
        "ambiente",
        "emision",
        "razon social",
        "nombres y apellidos",
        "pedido no",
    }
    cfg = ocr_runtime or load_ocr_runtime_config(None)
    skip_markers = _runtime_normalized_text_set(
        cfg,
        "invoice_line_skip_markers",
        list(_DEFAULT_OCR_CONFIG["invoice_line_skip_markers"]),
    )
    skip_markers.update({"razon social", "nombres y apellidos", "pedido no"})

    candidates: list[tuple[float, dict[str, Any]]] = []
    for raw_line in lines:
        line = _normalize_invoice_ocr_line(raw_line, ocr_runtime=cfg)
        line = line.replace("|", " ")
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        normalized = _normalize_evidence_text(line)
        if any(marker in normalized for marker in skip_markers):
            continue

        tokens = line.split()
        numeric_tokens: list[tuple[int, float, str]] = []
        for idx, token in enumerate(tokens):
            digits = _digits_only(token)
            if not digits or len(digits) > 8:
                continue
            if _token_looks_like_invoice_code(token):
                continue
            # Excluir tokens con sufijo de letra (duraciones "743h", "59m", unidades "1kg")
            # — representan tiempo o unidades de medida, no cantidades ni precios
            if re.search(r"\d[a-zA-Z]$", token):
                continue
            parsed = safe_floatish(token)
            if parsed is None:
                continue
            numeric_tokens.append((idx, parsed, token))
        if len(numeric_tokens) < 3:
            continue

        qty_idx, quantity, _ = numeric_tokens[0]
        unit_idx, unit_price, _ = numeric_tokens[-2]
        total_idx, total_price, _ = numeric_tokens[-1]
        if qty_idx >= unit_idx or unit_idx >= total_idx:
            continue

        description = " ".join(tokens[qty_idx + 1 : unit_idx]).strip()
        # Eliminar monedas/símbolos sueltos al inicio o final y limpiar puntuación
        description = re.sub(r"^[$€£¥]\s*|[$€£¥]\s*$", "", description)
        description = " ".join(description.split()).strip(" -–—|/.,;:()[]{}")
        description = _normalize_invoice_description_strict(description)
        if not description:
            continue
        if _normalize_evidence_text(description) in {
            "razon social nombres y apellidos",
            "nombres y apellidos",
        }:
            continue

        candidate_score = 0.0
        if quantity > 0:
            candidate_score += 2.0
        if unit_price > 0:
            candidate_score += 2.0
        if total_price > 0:
            candidate_score += 4.0
        if len(description.split()) >= 2:
            candidate_score += 1.0
        if _value_token_evidence(text_normalized, description):
            candidate_score += 1.0
        if total_price > 0 and total_price >= unit_price:
            candidate_score += 1.0

        row: dict[str, Any] = {
            "description": description,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
        }
        candidates.append((candidate_score, row))

    if not candidates:
        # Fallback: formato POS ticket "1.00x descripcion $2.50"
        pos_items = _extract_pos_ticket_items_from_ocr(text)
        if pos_items:
            return pos_items
        return []

    deduped: dict[str, tuple[float, dict[str, Any]]] = {}
    for score, row in candidates:
        key = _normalize_evidence_text(str(row.get("description") or ""))
        if not key:
            continue
        current = deduped.get(key)
        if current is None or score > current[0]:
            deduped[key] = (score, row)

    return [row for _score, row in sorted(deduped.values(), key=lambda item: item[0], reverse=True)]


def _field_appears_only_after_customer_block(content: str, value: Any) -> bool:
    value_norm = _normalize_evidence_text(value)
    text_norm = _normalize_evidence_text(content)
    if not value_norm or len(value_norm) < 4 or not text_norm:
        return False
    marker_indexes = [
        idx
        for marker in ("datos del cliente", "razon social", "nombres y apellidos")
        if (idx := text_norm.find(marker)) >= 0
    ]
    if not marker_indexes:
        return False
    marker_index = min(marker_indexes)
    return value_norm in text_norm[marker_index:] and value_norm not in text_norm[:marker_index]


def _looks_like_customer_party_value(value: Any) -> bool:
    norm = _normalize_evidence_text(value)
    return any(
        token in norm
        for token in (
            "razon social",
            "nombres y apellidos",
            "datos del cliente",
            "cliente",
        )
    )


def _line_items_total_from_fields(fields: dict[str, Any]) -> float | None:
    items = fields.get("line_items")
    if not isinstance(items, list):
        return None
    total = 0.0
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_total = safe_floatish(item.get("total_price"))
        if item_total is None:
            quantity = safe_floatish(item.get("quantity"))
            unit_price = safe_floatish(item.get("unit_price"))
            if quantity is not None and unit_price is not None:
                item_total = round(quantity * unit_price, 2)
        if item_total is None or item_total <= 0:
            continue
        total += float(item_total)
        count += 1
    return round(total, 2) if count else None


def _repair_total_from_line_items_or_subtotal(fields: dict[str, Any]) -> bool:
    current_total = safe_floatish(fields.get("total_amount"))
    line_items_total = _line_items_total_from_fields(fields)
    subtotal = safe_floatish(fields.get("subtotal"))
    tax_amount = safe_floatish(fields.get("tax_amount"))

    preferred: float | None = None
    if line_items_total is not None:
        preferred = line_items_total
    elif subtotal is not None and (tax_amount is None or abs(float(tax_amount)) <= 0.01):
        preferred = subtotal

    if preferred is None or preferred <= 0:
        return False
    if current_total is None:
        fields["total_amount"] = preferred
        return True

    tolerance = max(5.0, abs(float(current_total)) * 0.02)
    has_matching_subtotal = subtotal is not None and abs(float(subtotal) - preferred) <= 1.0
    clearly_too_small = float(current_total) < preferred * 0.2
    close_ocr_digit_error = abs(float(current_total) - preferred) <= tolerance
    if has_matching_subtotal or clearly_too_small or close_ocr_digit_error:
        if abs(float(current_total) - preferred) > 0.01:
            fields["total_amount"] = preferred
            return True
    return False


def _apply_invoice_ocr_rescue(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
    ocr_runtime: dict[str, Any] | None = None,
) -> list[str]:
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return []

    normalized_format = str(format_hint or "").strip().upper()
    cfg = ai_runtime or load_ai_runtime_config(None)
    evidence_formats = {
        str(item).strip().upper()
        for item in (cfg.get("ocr_evidence_formats") or [])
        if str(item).strip()
    }
    if normalized_format not in evidence_formats:
        return []

    doc_type = str(parsed.get("doc_type") or "").strip().upper()
    text_normalized = _normalize_evidence_text(content)
    invoice_like = (
        doc_type
        in {
            "INVOICE",
            "SUPPLIER_INVOICE",
            "PURCHASE_INVOICE",
            "COMMERCIAL_INVOICE",
        }
        or any(
            token in text_normalized
            for token in ("factura", "invoice", "nota de venta", "comprobante", "boleta")
        )
        or (
            ("ruc" in text_normalized or re.search(r"\b\d{3}-\d{3}-\d{6,12}\b", content))
            and any(
                token in text_normalized
                for token in ("valor total", "subtotal", "sub total", "datos del cliente")
            )
        )
    )
    if not invoice_like:
        return []

    repaired_fields: list[str] = []

    # Use the unified vendor extractor so the AI repair path and the OCR text
    # fallback agree on the vendor inference logic.
    from .field_extractors import extract_vendor_name as _unified_extract_vendor_name

    ocr_vendor = _unified_extract_vendor_name(text=content, ocr_runtime=ocr_runtime)
    try:
        from .invoice_ocr_rescue import _rescue_vendor as _rescue_invoice_vendor

        rescued_vendor = _rescue_invoice_vendor(content)
        if rescued_vendor:
            ocr_vendor = rescued_vendor
    except Exception:
        pass
    current_vendor = fields.get("vendor")
    if ocr_vendor and (
        current_vendor in (None, "")
        or not _value_token_evidence(text_normalized, current_vendor)
        or _looks_like_customer_party_value(current_vendor)
        or _field_appears_only_after_customer_block(content, current_vendor)
    ):
        fields["vendor"] = ocr_vendor
        repaired_fields.append("vendor")

    ocr_doc_number = _extract_invoice_doc_number_from_ocr(content, ocr_runtime=ocr_runtime)
    current_doc_number = fields.get("doc_number")
    if ocr_doc_number and (
        current_doc_number in (None, "")
        or _digits_only(current_doc_number) != _digits_only(ocr_doc_number)
        or not _value_token_evidence(text_normalized, current_doc_number, min_len=3, ai_runtime=cfg)
    ):
        fields["doc_number"] = ocr_doc_number
        repaired_fields.append("doc_number")

    ocr_line_items = _extract_invoice_line_items_from_ocr(content, ocr_runtime=ocr_runtime)
    current_line_items = fields.get("line_items")
    current_line_items_list = current_line_items if isinstance(current_line_items, list) else []
    if ocr_line_items and (
        not current_line_items_list
        or not _line_items_evidence(
            text_normalized,
            _digits_only(content),
            current_line_items_list,
            ai_runtime=cfg,
        )
    ):
        fields["line_items"] = ocr_line_items
        repaired_fields.append("line_items")

    return repaired_fields


def _apply_high_evidence_ocr_repairs(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    prompt_config: dict[str, Any] | None = None,
    ai_runtime: dict[str, Any] | None = None,
    ocr_runtime: dict[str, Any] | None = None,
) -> None:
    cfg = ai_runtime or load_ai_runtime_config(None)
    normalized_format = str(format_hint or "").strip().upper()
    evidence_formats = {
        str(item).strip().upper()
        for item in (cfg.get("ocr_evidence_formats") or [])
        if str(item).strip()
    }
    if normalized_format not in evidence_formats:
        return

    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return

    # Unified field extractors live in field_extractors. They combine the
    # labelled-amount logic from this module with the line-inference fallback
    # from text_fallback_extractor so that the AI repair path and the OCR
    # fallback path produce consistent values for the same OCR text.
    from .field_extractors import extract_issue_date as _unified_extract_issue_date
    from .field_extractors import extract_total_amount as _unified_extract_total_amount

    quality = _estimate_text_quality(content, ai_runtime=cfg)
    labeled_total = _unified_extract_total_amount(text=content, prompt_config=prompt_config)
    labeled_subtotal = _extract_labeled_amount(content, "subtotal", prompt_config=prompt_config)
    labeled_tax = _extract_labeled_amount(content, "tax_amount", prompt_config=prompt_config)
    ocr_issue_date = _unified_extract_issue_date(text=content)

    if labeled_tax is not None and ocr_issue_date:
        try:
            issue_year, issue_month, issue_day = (int(part) for part in ocr_issue_date.split("-"))
            tax_value = float(labeled_tax)
            if tax_value.is_integer() and int(tax_value) in {issue_year, issue_month, issue_day}:
                labeled_tax = None
        except (TypeError, ValueError):
            pass

    if quality["score"] < max(0.0, min(1.0, float(cfg.get("ocr_min_quality") or 0.45))) and not any(
        value is not None
        for value in (labeled_total, labeled_subtotal, labeled_tax, ocr_issue_date)
    ):
        return

    text_digits = _digits_only(content)

    # Note: the legacy contextual-max fallback is already chained inside
    # ``extract_total_amount`` (step 2) so we no longer call
    # ``_extract_contextual_max_amount`` here directly.
    _repairs: list[str] = []

    current_total = fields.get("total_amount")
    if labeled_total is not None and (
        current_total in (None, "")
        or not _numeric_evidence(text_digits, current_total)
        or abs(float(current_total) - labeled_total) > 1.0
    ):
        if current_total not in (None, "") and current_total != labeled_total:
            _repairs.append(f"total_amount: {current_total!r} → {labeled_total!r}")
        fields["total_amount"] = labeled_total
    elif current_total not in (None, "") and not _amount_has_monetary_context(
        content, current_total, field_name="total_amount", ocr_runtime=ocr_runtime
    ):
        _repairs.append(
            f"total_amount: {current_total!r} → None (sin evidencia monetaria suficiente)"
        )
        fields["total_amount"] = None

    current_subtotal = fields.get("subtotal")
    total_ceiling = fields.get("total_amount")
    if labeled_subtotal is not None:
        if total_ceiling not in (None, ""):
            try:
                if float(labeled_subtotal) <= 0 and float(total_ceiling) > 0:
                    labeled_subtotal = None
                elif float(labeled_subtotal) > float(total_ceiling) + 0.01:
                    labeled_subtotal = None
            except (TypeError, ValueError):
                pass
    if labeled_subtotal is not None and (
        current_subtotal in (None, "") or not _numeric_evidence(text_digits, current_subtotal)
    ):
        if current_subtotal not in (None, "") and current_subtotal != labeled_subtotal:
            _repairs.append(f"subtotal: {current_subtotal!r} → {labeled_subtotal!r}")
        fields["subtotal"] = labeled_subtotal
    elif (
        labeled_subtotal is None
        and current_subtotal not in (None, "")
        and not _numeric_evidence(text_digits, current_subtotal)
    ):
        _repairs.append(f"subtotal: {current_subtotal!r} → None (sin evidencia numérica)")
        fields["subtotal"] = None

    current_tax = fields.get("tax_amount")
    if labeled_tax is not None and (
        current_tax in (None, "") or not _numeric_evidence(text_digits, current_tax)
    ):
        if current_tax not in (None, "") and current_tax != labeled_tax:
            _repairs.append(f"tax_amount: {current_tax!r} → {labeled_tax!r}")
        fields["tax_amount"] = labeled_tax
    elif (
        labeled_tax is None
        and current_tax not in (None, "")
        and not _numeric_evidence(text_digits, current_tax)
    ):
        _repairs.append(f"tax_amount: {current_tax!r} → None (sin evidencia numérica)")
        fields["tax_amount"] = None

    issue_date = fields.get("issue_date")
    if ocr_issue_date and (
        issue_date in (None, "") or not _numeric_evidence(text_digits, issue_date)
    ):
        if issue_date not in (None, "") and issue_date != ocr_issue_date:
            _repairs.append(f"issue_date: {issue_date!r} → {ocr_issue_date!r}")
        fields["issue_date"] = ocr_issue_date

    current_vendor_tax_id = fields.get("vendor_tax_id")
    ocr_vendor_tax_id = _extract_tax_id_from_ocr(content)
    if ocr_vendor_tax_id and (
        current_vendor_tax_id in (None, "")
        or _digits_only(current_vendor_tax_id) != ocr_vendor_tax_id
        or not _numeric_evidence(text_digits, current_vendor_tax_id)
    ):
        if current_vendor_tax_id not in (None, "") and current_vendor_tax_id != ocr_vendor_tax_id:
            _repairs.append(f"vendor_tax_id: {current_vendor_tax_id!r} → {ocr_vendor_tax_id!r}")
        fields["vendor_tax_id"] = ocr_vendor_tax_id
    elif current_vendor_tax_id not in (None, "") and not _numeric_evidence(
        text_digits, current_vendor_tax_id
    ):
        _repairs.append(f"vendor_tax_id: {current_vendor_tax_id!r} → None (sin evidencia numérica)")
        fields["vendor_tax_id"] = None

    if _repairs:
        logger.info(
            "ocr_repair format=%s fields_overwritten=%d %s",
            normalized_format,
            len(_repairs),
            " | ".join(_repairs),
        )

    invoice_repaired_fields = _apply_invoice_ocr_rescue(
        parsed,
        content=content,
        format_hint=format_hint,
        ai_runtime=cfg,
        ocr_runtime=ocr_runtime,
    )
    if _repair_total_from_line_items_or_subtotal(fields):
        invoice_repaired_fields.append("total_amount")
    if invoice_repaired_fields:
        logger.info(
            "OCR invoice rescue applied (%s): %s",
            normalized_format or "UNKNOWN",
            ", ".join(invoice_repaired_fields),
        )


def _find_sequential_anchor_indexes(lines: list[str], anchors: list[str]) -> list[int]:
    indexes: list[int] = []
    search_start = 0
    normalized_lines = [_normalize_evidence_text(line) for line in lines]
    for anchor in anchors:
        anchor_norm = _normalize_evidence_text(anchor)
        if not anchor_norm:
            return []
        found_index = -1
        for idx in range(search_start, len(normalized_lines)):
            if anchor_norm in normalized_lines[idx]:
                found_index = idx
                break
        if found_index < 0:
            return []
        indexes.append(found_index)
        search_start = found_index + 1
    return indexes


def _rebuild_line_item_extra_columns_from_ocr(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    ai_runtime: dict[str, Any] | None = None,
) -> None:
    cfg = ai_runtime or load_ai_runtime_config(None)
    normalized_format = str(format_hint or "").strip().upper()
    evidence_formats = {
        str(item).strip().upper()
        for item in (cfg.get("ocr_evidence_formats") or [])
        if str(item).strip()
    }
    if normalized_format not in evidence_formats:
        return

    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return
    items = fields.get("line_items")
    if not isinstance(items, list) or len(items) < 2:
        return

    line_items = [item for item in items if isinstance(item, dict)]
    if len(line_items) < 2:
        return

    descriptions = [str(item.get("description") or "").strip() for item in line_items]
    if any(not desc for desc in descriptions):
        return

    lines = [str(line).strip() for line in str(content or "").splitlines() if str(line).strip()]
    if len(lines) < len(line_items) * 2:
        return

    anchor_indexes = _find_sequential_anchor_indexes(lines, descriptions)
    if len(anchor_indexes) < len(line_items):
        return

    gap_sizes = [
        next_index - current_index
        for current_index, next_index in zip(anchor_indexes, anchor_indexes[1:])
        if next_index > current_index
    ]
    candidate_cell_count = min(gap_sizes) if gap_sizes else 0
    if candidate_cell_count < 4 or candidate_cell_count > 8:
        return

    header_start = anchor_indexes[0] - candidate_cell_count
    if header_start < 0:
        return
    header_labels = lines[header_start : anchor_indexes[0]]
    if len(header_labels) != candidate_cell_count:
        return

    for item, start_index in zip(line_items, anchor_indexes):
        row_cells = lines[start_index : start_index + candidate_cell_count]
        if len(row_cells) != candidate_cell_count:
            continue

        quantity_digits = _digits_only(item.get("quantity"))
        unit_price_digits = _digits_only(item.get("unit_price"))
        total_price_digits = _digits_only(item.get("total_price"))
        matched_positions: set[int] = {0}

        for pos, cell in enumerate(row_cells[1:], start=1):
            cell_digits = _digits_only(cell)
            if quantity_digits and cell_digits == quantity_digits and "quantity" in item:
                matched_positions.add(pos)
                continue
            if unit_price_digits and cell_digits == unit_price_digits and "unit_price" in item:
                matched_positions.add(pos)
                continue
            if total_price_digits and cell_digits == total_price_digits and "total_price" in item:
                matched_positions.add(pos)
                continue

        extra_columns = item.get("extra_columns")
        if not isinstance(extra_columns, dict):
            extra_columns = {}

        for pos, cell in enumerate(row_cells):
            if pos in matched_positions:
                continue
            header_label = str(header_labels[pos] or "").strip()
            cell_value = str(cell or "").strip()
            if not header_label or not cell_value:
                continue
            extra_columns.setdefault(header_label, cell_value)

        if extra_columns:
            item["extra_columns"] = extra_columns


def _build_additional_field_hints(
    recipe_config: dict | None,
    prompt_config: dict | None = None,
) -> str:
    rc = recipe_config or {}
    field_descriptions = rc.get("field_descriptions") or {}
    if not isinstance(field_descriptions, dict):
        return ""

    lines: list[str] = []
    for raw_key, raw_value in field_descriptions.items():
        key = str(raw_key or "").strip()
        value = str(raw_value or "").strip()
        if not key or not value or key in {"subtotal", "tax_amount"}:
            continue
        lines.append(f'- "{key}": {value}')

    if not lines:
        return ""
    pc = prompt_config or {}
    preamble = str(
        pc.get("learned_hints_preamble")
        or "Learned hints from previously confirmed similar documents:"
    ).strip()
    return preamble + "\n" + "\n".join(lines)


def _resize_image_for_vision(image_bytes: bytes, max_dim: int = 1024) -> bytes:
    """Resize image so its longest side is at most max_dim pixels.

    Vision models don't need full-resolution photos — 1024px is sufficient
    to read invoice/receipt text. Keeping this small reduces base64 payload
    and inference time in Ollama, avoiding ReadTimeout on large WhatsApp images.
    """
    import io as _io

    from PIL import Image as _Image

    img = _Image.open(_io.BytesIO(image_bytes))
    w, h = img.size

    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, _Image.LANCZOS)
    else:
        new_size = (w, h)

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    buf = _io.BytesIO()
    img.save(buf, format="JPEG", quality=75)
    result = buf.getvalue()
    logger.debug(
        "Vision image %dx%d→%dx%d (%d→%d bytes)",
        w,
        h,
        new_size[0],
        new_size[1],
        len(image_bytes),
        len(result),
    )
    return result


def _vision_provider_config(ai_runtime: dict[str, Any]) -> dict[str, str]:
    provider = (
        str(
            os.getenv("IMPORTADOR_VISION_PROVIDER") or ai_runtime.get("vision_provider") or "ollama"
        )
        .strip()
        .lower()
    )
    if provider in {"openai", "openai_compatible", "openai-compatible", "compatible"}:
        provider = "openai_compatible"
    elif provider not in {"ollama", "openai_compatible"}:
        provider = "ollama"

    base_url = str(
        os.getenv("IMPORTADOR_VISION_ENDPOINT")
        or (os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434")
    ).rstrip("/")
    model = str(
        os.getenv("IMPORTADOR_VISION_MODEL")
        or os.getenv("OLLAMA_VISION_MODEL")
        or ai_runtime.get("vision_model")
        or "minicpm-v"
    ).strip()
    chat_path = str(
        os.getenv("IMPORTADOR_VISION_CHAT_PATH")
        or ("/api/chat" if provider == "ollama" else "/v1/chat/completions")
    ).strip()
    probe_path = str(
        os.getenv("IMPORTADOR_VISION_PROBE_PATH") or ("/api/tags" if provider == "ollama" else "")
    ).strip()
    skip_probe = str(os.getenv("IMPORTADOR_VISION_SKIP_PROBE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return {
        "provider": provider,
        "base_url": base_url,
        "model": model,
        "chat_path": chat_path or ("/api/chat" if provider == "ollama" else "/v1/chat/completions"),
        "probe_path": probe_path,
        "skip_probe": "1" if skip_probe else "0",
    }


async def _analyze_with_vision(
    image_bytes: bytes,
    filename: str,
    format_hint: str,
    ocr_content: str = "",
    recipe_config: dict | None = None,
    prompt_config: dict[str, Any] | None = None,
    pre_extracted_fields: dict[str, Any] | None = None,
    db: Any = None,
    timeout_override_secs: float | None = None,
) -> dict[str, Any] | None:
    """Try to analyze a document image using a vision-capable model.

    Returns None if no vision model is available, letting the caller fall back
    to the text-based OCR path.
    """
    import base64

    import httpx

    ai_runtime = load_ai_runtime_config(db)
    ocr_runtime = load_ocr_runtime_config(db)
    vision_cfg = _vision_provider_config(ai_runtime)
    vision_model = vision_cfg["model"]
    provider = vision_cfg["provider"]
    base_url = vision_cfg["base_url"]
    chat_path = vision_cfg["chat_path"]
    probe_path = vision_cfg["probe_path"]

    try:
        probe_timeout = max(
            1.0,
            float(
                os.getenv("IMPORTADOR_VISION_PROBE_TIMEOUT")
                or ai_runtime.get("vision_probe_timeout_seconds")
                or 5.0
            ),
        )
        if provider == "ollama" and probe_path and vision_cfg["skip_probe"] != "1":
            async with httpx.AsyncClient(timeout=probe_timeout) as client:
                tags_resp = await client.get(f"{base_url}{probe_path}")
                if tags_resp.status_code != 200:
                    return None
                available = [m["name"].split(":")[0] for m in tags_resp.json().get("models", [])]
                if vision_model.split(":")[0] not in available:
                    logger.info(
                        "Vision model '%s' not available, falling back to OCR", vision_model
                    )
                    return None
    except Exception:
        return None

    rc = recipe_config or {}
    pc = prompt_config or load_prompt_config(None)
    system_prompt = (
        rc.get("prompt_system") or pc.get("extraction_system") or pc.get("vision_system_fallback")
    )

    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or "taxable base before tax. Number or null"
    _f_tax = _fd.get("tax_amount") or "total tax (VAT/IVA/IGV/GST). Number or null if absent"
    learned_hints = _build_additional_field_hints(recipe_config, prompt_config=pc)
    dynamic_fields_prompt = _build_dynamic_fields_prompt(
        None,
        {
            **_fd,
            "subtotal": _f_subtotal,
            "tax_amount": _f_tax,
        },
        prompt_config=pc,
    )

    current_year = datetime.datetime.now().year
    vision_preamble = str(pc.get("vision_extraction_preamble") or "").strip()
    doc_type_instruction = str(pc.get("doc_type_instruction") or "").strip()
    critical_rules = _build_configured_rules(
        prompt_config=pc,
        current_year=current_year,
        vision_mode=True,
    )
    critical_rules_text = "\n".join(f"- {rule}" for rule in critical_rules)
    response_contract = _build_json_response_contract(
        dynamic_fields_prompt=dynamic_fields_prompt,
        doc_type_instruction=doc_type_instruction,
        is_table_literal="false",
        columns_literal="[]",
        reasoning_hint="brief explanation",
    )
    response_label = str(pc.get("response_json_label") or "Respond ONLY with valid JSON:").strip()
    critical_rules_heading = str(pc.get("critical_rules_heading") or "CRITICAL rules:").strip()
    additional_instructions_heading = str(
        pc.get("additional_instructions_heading") or "Additional instructions:"
    ).strip()
    pre_extracted_block = ""
    if isinstance(pre_extracted_fields, dict) and pre_extracted_fields:
        pre_extracted_block = (
            "OCR HINTS (extracted from text layer before vision; may be inaccurate "
            "due to image noise, logos or handwriting — treat as low-confidence reference, "
            "always prefer what you directly see in the image):\n"
            f"{json.dumps(pre_extracted_fields, ensure_ascii=False, indent=2, default=str)}\n\n"
        )

    user_prompt = (
        f"File: {filename} | Format: {format_hint}\n"
        f"{_build_document_time_context(pc, current_year=current_year)}\n\n"
        f"{pre_extracted_block}"
        f"{vision_preamble}\n"
        f"{response_label}\n"
        f"{response_contract}\n"
        f"{critical_rules_heading}\n"
        f"{critical_rules_text}"
    )

    custom_user = rc.get("prompt_user")
    if custom_user:
        user_prompt += f"\n\n{additional_instructions_heading}\n{custom_user}"
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    prompt_trace = _build_prompt_trace(
        mode="vision",
        system_prompt=str(system_prompt),
        user_prompt=user_prompt,
        response_contract=response_contract,
        critical_rules=critical_rules,
        doc_type_instruction=doc_type_instruction,
        learned_hints=learned_hints or None,
        custom_user_prompt=str(custom_user or "").strip() or None,
        prompt_messages=[
            {"role": "system", "content": str(system_prompt)},
            {"role": "user", "content": user_prompt},
        ],
    )

    resize_max_dim = max(64, int(ai_runtime.get("vision_resize_max_dim") or 1024))
    img_b64 = base64.b64encode(
        _resize_image_for_vision(image_bytes, max_dim=resize_max_dim)
    ).decode("utf-8")

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    if provider == "ollama":
        messages[-1]["images"] = [img_b64]

    payload: dict[str, Any] = {
        "model": vision_model,
        "messages": messages,
        "stream": False,
        "temperature": float(ai_runtime.get("vision_temperature") or 0.1),
    }
    if provider == "ollama":
        payload["options"] = {
            "temperature": float(ai_runtime.get("vision_temperature") or 0.1),
            "num_predict": max(1, int(ai_runtime.get("vision_num_predict") or 600)),
        }
    else:
        payload["max_tokens"] = max(1, int(ai_runtime.get("vision_num_predict") or 600))
        payload["temperature"] = float(ai_runtime.get("vision_temperature") or 0.1)
        payload["messages"][-1]["content"] = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
        ]

    try:
        timeout_secs = max(
            1.0,
            float(
                timeout_override_secs
                or os.getenv("IMPORTADOR_VISION_TIMEOUT")
                or os.getenv("OLLAMA_VISION_TIMEOUT")
                or ai_runtime.get("vision_timeout_seconds")
                or os.getenv("OLLAMA_TIMEOUT", "30")
            ),
        )
        timeout = httpx.Timeout(timeout_secs, read=timeout_secs)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}{chat_path}", json=payload)
        resp.raise_for_status()
        data = resp.json()

        if provider == "ollama":
            raw_content = (data.get("message") or {}).get("content", "")
        else:
            choices = data.get("choices") or []
            message = choices[0].get("message") if choices else {}
            raw_content = (message or {}).get("content", "")
        model_used = data.get("model") or vision_model

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            # Images are never tabular structured data — force is_table=False
            # so fields are stored as invoice/receipt fields, not as row data.
            parsed["is_table"] = False
            parsed["columns"] = []
            parsed.setdefault("fields", {})
            parsed.setdefault("confidence", 0.8)
            parsed.setdefault(
                "reasoning",
                str(ai_runtime.get("vision_default_reasoning") or "Vision model analysis"),
            )
            _clean_vision_fields(parsed.get("fields") or {})
            _apply_low_evidence_guard(
                parsed,
                content=ocr_content,
                format_hint=format_hint,
                ai_runtime=ai_runtime,
            )
            _rebuild_line_item_extra_columns_from_ocr(
                parsed,
                content=ocr_content,
                format_hint=format_hint,
                ai_runtime=ai_runtime,
            )
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_full"] = prompt_trace["full_prompt"]
            parsed["prompt_parts"] = prompt_trace
            logger.info("Vision analysis succeeded with %s for %s", model_used, filename)
            return _finalize_analysis_payload(
                parsed,
                content=ocr_content,
                format_hint=format_hint,
                ai_runtime=ai_runtime,
                ocr_runtime=ocr_runtime,
                analysis_path="ai_vision",
            )

        logger.warning("Vision model returned unparseable response for %s", filename)
        return None

    except httpx.ReadTimeout:
        logger.warning(
            "Vision analysis timed out for %s after %.1fs using %s",
            filename,
            timeout_secs,
            vision_model,
        )
        return None
    except Exception as exc:
        logger.warning("Vision analysis failed for %s: %s", filename, exc, exc_info=True)
        return None


def _structured_payload_to_fields(
    structured_data: Any,
    structured_metadata: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    fields: dict[str, Any] = {}
    columns: list[str] = []

    if isinstance(structured_data, dict):
        fields = {
            str(key): value
            for key, value in structured_data.items()
            if not str(key).startswith("_")
        }
        columns = [str(key) for key in structured_data.keys() if not str(key).startswith("_")]
    elif isinstance(structured_data, list):
        rows = [dict(row) for row in structured_data if isinstance(row, dict)]
        if rows:
            cleaned_rows: list[dict[str, Any]] = []
            for row in rows:
                cleaned_row = {
                    str(key): value for key, value in row.items() if not str(key).startswith("_")
                }
                if cleaned_row:
                    cleaned_rows.append(cleaned_row)
            if cleaned_rows:
                fields["line_items"] = cleaned_rows
                columns = [str(key) for key in cleaned_rows[0].keys()]

    if isinstance(structured_metadata, dict):
        for value in structured_metadata.values():
            if isinstance(value, dict):
                for key, item in value.items():
                    if item is None:
                        continue
                    key_name = str(key)
                    if key_name.startswith("_"):
                        continue
                    fields.setdefault(key_name, item)
                    if key_name not in columns:
                        columns.append(key_name)
            elif (
                isinstance(value, list) and value and all(isinstance(item, dict) for item in value)
            ):
                fields.setdefault("line_items", value)

    return fields, columns


def _structured_direct_analysis(
    *,
    content: str,
    filename: str,
    format_hint: str,
    structured_data: Any,
    structured_metadata: dict[str, Any] | None,
    recipe_config: dict[str, Any] | None,
    fallback_patterns: dict[str, list[str]] | None,
) -> dict[str, Any]:
    fields, columns = _structured_payload_to_fields(structured_data, structured_metadata)
    prompt_parts = _build_prompt_trace(
        mode="structured_bypass",
        system_prompt="",
        user_prompt=f"File: {filename} | Format: {format_hint}",
        response_contract="",
        critical_rules=[],
        doc_type_instruction="",
        prompt_messages=[],
    )

    doc_type_hint = str((recipe_config or {}).get("doc_type_hint") or "").strip().upper()
    confidence_hint = float((recipe_config or {}).get("doc_type_hint_confidence") or 0.0)
    fallback_guess = _fallback_classify(
        content or json.dumps(structured_data or {}, ensure_ascii=False),
        filename,
        fallback_patterns,
    )
    doc_type = doc_type_hint or fallback_guess.get("doc_type", "OTHER")
    confidence = max(confidence_hint, 0.86 if fields else 0.72)

    result = {
        "doc_type": doc_type,
        "confidence": confidence,
        "reasoning": "Structured bypass: parsed CSV/Excel/JSON directly without LLM.",
        "is_table": bool(fields.get("line_items")) or isinstance(structured_data, list),
        "columns": columns,
        "fields": fields,
        "raw_response": "structured_bypass",
        "model_used": "structured-direct",
        "prompt_full": "",
        "prompt_parts": prompt_parts,
        "analysis_path": "structured_direct",
        "cache_hit": False,
        "cache_bypassed": False,
    }
    return _finalize_analysis_payload(
        result,
        content=content,
        format_hint=format_hint,
        ai_runtime=load_ai_runtime_config(None),
        ocr_runtime=load_ocr_runtime_config(None),
        analysis_path="structured_direct",
    )


def _build_reprocess_recipe_config(
    recipe_config: dict | None,
    *,
    db: Any,
    reprocess_mode: str,
    deep_reprocess_context: dict[str, Any] | None,
    deep_focus_fields: list[str] | None,
) -> tuple[dict[str, Any], str | None]:
    deep_active = str(reprocess_mode or "").strip().lower() == "deep"
    reprocess_control = load_reprocess_control(db)
    provider_override: str | None = None
    if deep_active and bool(reprocess_control.get("enable_premium_deep_reprocess")):
        provider_override = (
            str(reprocess_control.get("deep_premium_provider") or "").strip() or None
        )

    effective_recipe_config = dict(recipe_config or {})
    if not deep_active:
        return effective_recipe_config, provider_override

    deep_focus = [str(field).strip() for field in (deep_focus_fields or []) if str(field).strip()]
    deep_context = deep_reprocess_context or {}
    deep_suffix = str(reprocess_control.get("deep_reprocess_prompt_suffix") or "").strip()
    deep_lines: list[str] = []
    if deep_suffix:
        deep_lines.append(deep_suffix)
    if deep_focus:
        deep_lines.append(
            "Prioritize these missing required fields if visible: " + ", ".join(deep_focus)
        )
    previous_doc_type = str(deep_context.get("previous_doc_type") or "").strip()
    previous_confidence = deep_context.get("previous_confidence")
    if previous_doc_type or previous_confidence is not None:
        previous_bits: list[str] = []
        if previous_doc_type:
            previous_bits.append(previous_doc_type)
        if previous_confidence is not None:
            try:
                previous_bits.append(f"{float(previous_confidence):.2f}")
            except (TypeError, ValueError):
                pass
        if previous_bits:
            deep_lines.append("Previous pass summary: " + " / ".join(previous_bits))
    if deep_lines:
        prompt_system = str(effective_recipe_config.get("prompt_system") or "").strip()
        prompt_suffix = "\n".join(f"- {line}" for line in deep_lines)
        effective_recipe_config["prompt_system"] = "\n\n".join(
            part for part in [prompt_system, prompt_suffix] if part
        )
    prompt_user = str(effective_recipe_config.get("prompt_user") or "").strip()
    deep_prompt_user = "Deep reprocess: validate missing required fields first and re-read the document from scratch."
    effective_recipe_config["prompt_user"] = "\n\n".join(
        part for part in [prompt_user, deep_prompt_user] if part
    )
    return effective_recipe_config, provider_override


async def analyze_document(
    content: str,
    filename: str = "",
    format_hint: str = "",
    has_structured_rows: bool = False,
    recipe_config: dict | None = None,
    structured_data: Any | None = None,
    structured_metadata: dict[str, Any] | None = None,
    pre_extracted_fields: dict[str, Any] | None = None,
    image_bytes: bytes | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
    prompt_config: dict[str, Any] | None = None,
    db: Any = None,
    reprocess_mode: str = "fast",
    bypass_cache: bool = False,
    deep_reprocess_context: dict[str, Any] | None = None,
    deep_focus_fields: list[str] | None = None,
    timeout_override: float | None = None,
    force_vision: bool = False,
    vision_first: bool = True,
) -> dict[str, Any]:
    """Analyzes any accounting document with a single LLM call.

    Works with documents in ANY language (Spanish, English, German, French, etc.).
    The AI reads whatever is in the document and maps it to standard neutral output keys.

    For Excel/CSV with pre-parsed rows (has_structured_rows=True):
      - Receives headers + sample rows
      - LLM classifies the type and confirms column names
      - Actual rows come from the parser (structured_data), not the LLM

    For PDF/image/XML/TXT (has_structured_rows=False):
      - Receives text extracted by OCR
      - LLM classifies + extracts all fields

    Returns: {
        "doc_type": str,
        "confidence": float,
        "reasoning": str,
        "is_table": bool,
        "columns": list[str],   # if is_table=True
        "fields": dict,         # if is_table=False
        "raw_response": str,
        "model_used": str,
        "prompt_full": str,
    }
    """
    deep_active = str(reprocess_mode or "").strip().lower() == "deep"
    recipe_config, provider_override = _build_reprocess_recipe_config(
        recipe_config,
        db=db,
        reprocess_mode=reprocess_mode,
        deep_reprocess_context=deep_reprocess_context,
        deep_focus_fields=deep_focus_fields,
    )
    if (
        structured_data is not None
        and not deep_active
        and (
            has_structured_rows
            or str(format_hint or "").strip().upper() in {"CSV", "EXCEL", "JSON"}
        )
    ):
        return _structured_direct_analysis(
            content=content,
            filename=filename,
            format_hint=format_hint,
            structured_data=structured_data,
            structured_metadata=structured_metadata,
            recipe_config=recipe_config,
            fallback_patterns=fallback_patterns,
        )

    if has_structured_rows:
        return await _analyze_structured_document(
            content,
            filename,
            format_hint,
            recipe_config,
            fallback_patterns=fallback_patterns,
            prompt_config=prompt_config,
            db=db,
            bypass_cache=bypass_cache or deep_active,
            provider_override=provider_override,
        )

    ai_runtime = load_ai_runtime_config(db)
    ocr_runtime = load_ocr_runtime_config(db)

    _use_vision = force_vision and bool(image_bytes)
    if not _use_vision and not has_structured_rows:
        _use_vision = _should_use_vision_fallback(
            content, format_hint, image_bytes, ai_runtime=ai_runtime
        )

    # ── Fase visión-primero (OCR malo / docs visuales) ───────────────────────
    # Si vision_first=True intentamos visión antes que texto.
    # Si visión acierta, no ejecutamos texto (condición de parada).
    # Cada fase usa el mismo `timeout_override` (presupuesto por fase).
    if _use_vision and vision_first:
        if force_vision:
            logger.info(
                "force_vision=true vision_first=true filename=%s format=%s", filename, format_hint
            )
        vision_result = await _analyze_with_vision(
            image_bytes,
            filename,
            format_hint,
            content,
            recipe_config,
            prompt_config,
            pre_extracted_fields,
            db=db,
            timeout_override_secs=timeout_override,
        )
        if vision_result:
            logger.info(
                "pdf_second_phase_skipped reason=primary_success filename=%s format=%s path=%s",
                filename,
                format_hint,
                vision_result.get("analysis_path", "ai_vision"),
            )
            return vision_result
        # Visión falló/timeout; texto continúa con el mismo timeout por fase.
        logger.info(
            "vision_phase_failed_fallback_to_text filename=%s format=%s",
            filename,
            format_hint,
        )
        _use_vision = False  # ya intentado; no reintentar después del texto

    rc = dict(recipe_config or {})
    pc = prompt_config or load_prompt_config(None)
    ai_params = load_ai_params(db)
    system_prompt = rc.get("prompt_system") or pc.get("extraction_system")

    # Field descriptions can be customized per tenant via recipe_config["field_descriptions"].
    # Defaults are intentionally generic — locale-specific hints belong in the DB config.
    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or (
        "taxable base amount before tax (subtotal, net, base imponible, or similar). Number or null"
    )
    _f_tax = _fd.get("tax_amount") or (
        "total tax amount (VAT/IVA/IGV/GST/TVA or equivalent). Use 0 if present but zero. Number or null if absent"
    )
    learned_hints = _build_additional_field_hints(recipe_config, prompt_config=pc)
    dynamic_fields_prompt = _build_dynamic_fields_prompt(
        canonical_fields,
        {
            **_fd,
            "subtotal": _f_subtotal,
            "tax_amount": _f_tax,
        },
        prompt_config=pc,
    )

    tabular_note = (
        f"{pc.get('structured_table_note') or 'Structured table input.'}\n\n"
        if has_structured_rows
        else ""
    )

    content_limit = int(
        ai_params.get(
            "content_limit_structured" if has_structured_rows else "content_limit_unstructured"
        )
        or (4000 if has_structured_rows else 7000)
    )

    current_year = datetime.datetime.now().year
    doc_type_instruction = str(
        pc.get("doc_type_instruction")
        or "A short uppercase label describing the document type in English. "
        "Use standard business labels when they clearly apply. Use OTHER only if truly unclassifiable."
    ).strip()
    critical_rules = _build_configured_rules(
        prompt_config=pc,
        current_year=current_year,
        vision_mode=False,
    )
    critical_rules_text = "\n".join(f"- {rule}" for rule in critical_rules)
    response_contract = _build_json_response_contract(
        dynamic_fields_prompt=dynamic_fields_prompt,
        doc_type_instruction=doc_type_instruction,
        is_table_literal="true or false",
        columns_literal='["col1", "col2"]',
        reasoning_hint="brief explanation of classification",
    )
    response_label = str(pc.get("response_json_label") or "Respond ONLY with valid JSON:").strip()
    critical_rules_heading = str(pc.get("critical_rules_heading") or "CRITICAL rules:").strip()
    additional_instructions_heading = str(
        pc.get("additional_instructions_heading") or "Additional instructions:"
    ).strip()
    pre_extracted_block = ""
    if isinstance(pre_extracted_fields, dict) and pre_extracted_fields:
        pre_extracted_block = (
            "PRE-EXTRACTED HINTS (already obtained by deterministic tools; "
            "use them as input, do not ignore them):\n"
            f"{json.dumps(pre_extracted_fields, ensure_ascii=False, indent=2, default=str)}\n\n"
        )

    _doc_type_hint = rc.get("doc_type_hint")
    _hint_line = (
        f"HINT: Pre-classified as {_doc_type_hint} "
        f"(confidence={rc.get('doc_type_hint_confidence', 0):.2f}). "
        "Confirm or override based on content.\n"
        if _doc_type_hint
        else ""
    )
    user_prompt = (
        f"{tabular_note}"
        f"File: {filename} | Format: {format_hint}\n"
        f"{_build_document_time_context(pc, current_year=current_year)}\n"
        f"{_hint_line}\n"
        f"{pre_extracted_block}"
        f"Content:\n{_smart_content_sample(content, content_limit)}\n\n"
        f"{response_label}\n"
        f"{response_contract}\n"
        f"{critical_rules_heading}\n"
        f"{critical_rules_text}"
    )

    custom_user_prompt = rc.get("prompt_user")
    if custom_user_prompt:
        user_prompt += f"\n\n{additional_instructions_heading}\n{custom_user_prompt}"
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    full_prompt = system_prompt.rstrip() + "\n\n" + user_prompt
    transport_messages = [
        {"role": "system", "content": str(system_prompt)},
        {"role": "user", "content": user_prompt},
    ]
    prompt_trace = _build_prompt_trace(
        mode="text",
        system_prompt=str(system_prompt),
        user_prompt=user_prompt,
        response_contract=response_contract,
        critical_rules=critical_rules,
        doc_type_instruction=doc_type_instruction,
        learned_hints=learned_hints or None,
        custom_user_prompt=str(custom_user_prompt or "").strip() or None,
        prompt_messages=transport_messages,
    )
    fallback_context = _build_ai_fallback_policy_context(
        content=content,
        prompt_text=full_prompt,
        has_structured_rows=has_structured_rows,
        image_bytes=image_bytes,
        ai_runtime=ai_runtime,
        ai_params=ai_params,
    )

    # Resolver model y parámetros desde imp_config
    _doc_type_for_routing = (rc.get("doc_type_hint") or "").upper().strip() or None
    model_override = _sanitize_extraction_model_override(
        _resolve_model_for_doctype(_doc_type_for_routing, db)
    )
    temperature = float(ai_params.get("temperature") or 0.1)
    _by_dt: dict = ai_params.get("max_tokens_by_doctype") or {}
    max_tokens = int(
        _by_dt.get(_doc_type_for_routing or "") or ai_params.get("max_tokens_extraction") or 1500
    )

    # ── Fase texto (LLM) ────────────────────────────────────────────────────
    # El resultado se guarda en _text_result para poder intentar rescate de
    # visión después si el texto falló (modo texto-primero, vision_first=False).
    # Se inicializa con {} por defecto para evitar UnboundLocalError si una
    # excepción ocurre antes de asignarlo dentro del try.
    _text_result: dict[str, Any] = {}

    def _handle_classify_failure(
        *,
        raw_response: Any,
        model_used_value: str,
        analysis_path: str,
        cache_hit: bool,
    ) -> dict[str, Any]:
        """Construye un resultado de fallback con el mismo boilerplate repetido
        en los 3 caminos de error (response.is_error, parse_failure, exception)."""
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        _apply_high_evidence_ocr_repairs(
            fallback,
            content=content,
            format_hint=format_hint,
            prompt_config=pc,
            ai_runtime=ai_runtime,
            ocr_runtime=ocr_runtime,
        )
        fallback["raw_response"] = raw_response
        fallback["model_used"] = model_used_value
        fallback["prompt_full"] = full_prompt
        fallback["prompt_parts"] = prompt_trace
        fallback["analysis_path"] = analysis_path
        fallback["cache_hit"] = cache_hit
        fallback["cache_bypassed"] = bool(bypass_cache or deep_active)
        return fallback

    try:
        response = await AIService.query(
            task=AITask.EXTRACTION,
            prompt=full_prompt,
            messages=transport_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            context=fallback_context,
            module="importador",
            enable_recovery=True,
            model=model_override,
            provider=provider_override,
            bypass_cache=bypass_cache or deep_active,
            timeout_override=timeout_override,
        )

        raw_content = response.content
        model_used = response.model or "unknown"
        response_metadata = getattr(response, "metadata", None) or {}
        cache_hit_flag = bool(response_metadata.get("source") == "redis_cache")

        if response.is_error:
            logger.warning("AI analysis failed: %s", response.error)
            _text_result = _handle_classify_failure(
                raw_response=response.error,
                model_used_value=model_used,
                analysis_path="fallback",
                cache_hit=cache_hit_flag,
            )

        else:
            parsed = _parse_json_response(raw_content)
            if parsed and parsed.get("doc_type"):
                parsed.setdefault("is_table", False)
                parsed.setdefault("columns", [])
                parsed.setdefault("fields", {})
                parsed.setdefault("confidence", 0.7)
                parsed.setdefault("reasoning", "")
                # Compute field confidences on original AI fields before OCR
                # repairs mutate them; _finalize_analysis_payload will reuse
                # these pre-computed values instead of re-scoring repaired
                # fields.
                parsed["field_confidences"] = _build_field_confidences(
                    parsed.get("fields"),
                    content=content,
                    format_hint=format_hint,
                    ai_runtime=ai_runtime,
                    ocr_runtime=ocr_runtime,
                    analysis_path="ai_text",
                )
                _apply_low_evidence_guard(
                    parsed,
                    content=content,
                    format_hint=format_hint,
                    ai_runtime=ai_runtime,
                )
                _apply_high_evidence_ocr_repairs(
                    parsed,
                    content=content,
                    format_hint=format_hint,
                    prompt_config=pc,
                    ai_runtime=ai_runtime,
                    ocr_runtime=ocr_runtime,
                )
                _rebuild_line_item_extra_columns_from_ocr(
                    parsed,
                    content=content,
                    format_hint=format_hint,
                    ai_runtime=ai_runtime,
                )
                parsed["raw_response"] = raw_content
                parsed["model_used"] = model_used
                parsed["prompt_full"] = full_prompt
                parsed["prompt_parts"] = prompt_trace
                parsed["analysis_path"] = "ai_text"
                parsed["cache_hit"] = cache_hit_flag
                parsed["cache_bypassed"] = bool(bypass_cache or deep_active)
                _text_result = parsed
            else:
                _text_result = _handle_classify_failure(
                    raw_response=raw_content,
                    model_used_value=model_used,
                    analysis_path="fallback",
                    cache_hit=cache_hit_flag,
                )

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        _text_result = _handle_classify_failure(
            raw_response=str(exc),
            model_used_value="fallback",
            analysis_path="fallback_error",
            cache_hit=False,
        )

    # ── Rescate de visión en modo texto-primero ──────────────────────────────
    # Si el texto falló (fallback/fallback_error) y tenemos imagen disponible,
    # intentamos visión como segunda fase. El mismo timeout por fase aplica.
    # Condición de parada: si el texto fue "ai_text", no se ejecuta visión.
    if not vision_first and _use_vision:
        if _text_result.get("analysis_path") not in {"fallback", "fallback_error"}:
            # Texto primero tuvo éxito: no ejecutar visión
            logger.info(
                "pdf_second_phase_skipped reason=primary_success filename=%s format=%s path=%s",
                filename,
                format_hint,
                _text_result.get("analysis_path"),
            )

    if (
        not vision_first
        and _use_vision
        and _text_result.get("analysis_path") in {"fallback", "fallback_error"}
    ):
        logger.info(
            "text_first_vision_rescue filename=%s format=%s text_path=%s",
            filename,
            format_hint,
            _text_result.get("analysis_path"),
        )
        vision_result = await _analyze_with_vision(
            image_bytes,
            filename,
            format_hint,
            content,
            recipe_config,
            prompt_config,
            db=db,
            timeout_override_secs=timeout_override,
        )
        if vision_result:
            return vision_result

    return _finalize_analysis_payload(
        _text_result,
        content=content,
        format_hint=format_hint,
        ai_runtime=ai_runtime,
        ocr_runtime=ocr_runtime,
        analysis_path=str(_text_result.get("analysis_path") or ""),
    )


def _fallback_classify(
    text: str,
    filename: str,
    extra_patterns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Rule-based classification used only when the AI service is unavailable.

    Uses runtime-configured doc_type patterns plus any tenant-specific patterns
    passed via extra_patterns.
    """
    text_lower = text.lower()
    fn_lower = filename.lower()

    patterns = {**load_doc_type_patterns(None), **(extra_patterns or {})}

    best_type = "OTHER"
    best_score = 0.0
    for doc_type, keywords in patterns.items():
        matches = sum(1 for kw in keywords if kw in text_lower or kw in fn_lower)
        if matches > best_score:
            best_score = matches
            best_type = doc_type

    confidence = min(0.7, 0.3 + (best_score * 0.2)) if best_score > 0 else 0.2
    return {
        "doc_type": best_type,
        "confidence": confidence,
        "reasoning": f"Rule-based fallback (AI unavailable). Matches: {int(best_score)}",
    }


def _parse_json_response(content: str) -> dict | None:
    """Parses JSON from LLM response, handling markdown code blocks."""
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                pass
    return None
