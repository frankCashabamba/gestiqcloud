"""Universal AI analyzer for any accounting document in any language."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import unicodedata
from typing import Any

from app.modules.importador.runtime_config import (
    load_ai_model_routing,
    load_ai_params,
    load_ai_runtime_config,
    load_doc_type_patterns,
    load_prompt_config,
    load_reprocess_control,
    load_tax_id_patterns_config,
)
from app.services.ai.base import AITask, model_name
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")


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
    lowered = resolved.lower()
    if lowered.startswith(("qwen2.5-coder", "qwen2.5")):
        logger.warning("Ignoring legacy extraction routing model=%s", resolved)
        return None
    return resolved


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
    cfg = ai_runtime or load_ai_runtime_config(None)
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return {"score": 0.0, "chars": 0.0, "words": 0.0}

    chars = len(normalized)
    tokens = re.findall(r"[^\W_]{2,}", normalized, flags=re.UNICODE)
    word_count = len(tokens)
    alpha_chars = sum(1 for ch in normalized if ch.isalpha())
    alnum_chars = sum(1 for ch in normalized if ch.isalnum())
    weird_chars = sum(
        1
        for ch in normalized
        if not (ch.isalnum() or ch.isspace() or ch in ".,;:/-_#%()[]{}+*'\"@")
    )

    alpha_ratio = alpha_chars / max(alnum_chars, 1)
    weird_ratio = weird_chars / max(chars, 1)
    length_score = min(chars / max(float(cfg.get("ocr_length_target_chars") or 1200.0), 1.0), 1.0)
    word_score = min(word_count / max(float(cfg.get("ocr_word_target") or 180.0), 1.0), 1.0)
    alpha_score = min(
        alpha_ratio / max(float(cfg.get("ocr_alpha_ratio_target") or 0.6), 0.01),
        1.0,
    )
    noise_penalty = min(
        weird_ratio / max(float(cfg.get("ocr_noise_ratio_limit") or 0.2), 0.01),
        1.0,
    )

    score = (
        (length_score * float(cfg.get("ocr_score_weight_length") or 0.35))
        + (word_score * float(cfg.get("ocr_score_weight_words") or 0.35))
        + (alpha_score * float(cfg.get("ocr_score_weight_alpha") or 0.2))
        + ((1 - noise_penalty) * float(cfg.get("ocr_score_weight_clean") or 0.1))
    )
    return {
        "score": round(max(0.0, min(1.0, score)), 3),
        "chars": float(chars),
        "words": float(word_count),
        "alpha_ratio": round(alpha_ratio, 3),
        "weird_ratio": round(weird_ratio, 3),
    }


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
            "enabled": _context_bool("openai_fallback_enabled", True),
            "allow_on_error": _context_bool("openai_fallback_on_error", False),
            "allow_on_slow": _context_bool("openai_fallback_on_slow", True),
            "allow_on_complex": _context_bool("openai_fallback_on_complex", True),
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

        if response.is_error:
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": True, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = prompt[:500]
            fallback["prompt_full"] = prompt
            fallback["prompt_parts"] = prompt_parts
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
            parsed["is_table"] = True
            parsed["columns"] = []
            parsed["fields"] = {}
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = prompt[:500]
            parsed["prompt_full"] = prompt
            parsed["prompt_parts"] = prompt_parts
            parsed["analysis_path"] = "ai_structured"
            parsed["cache_hit"] = bool(response_metadata.get("source") == "redis_cache")
            parsed["cache_bypassed"] = bool(bypass_cache)
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = prompt[:500]
        fallback["prompt_full"] = prompt
        fallback["prompt_parts"] = prompt_parts
        fallback["analysis_path"] = "fallback"
        fallback["cache_hit"] = bool(response_metadata.get("source") == "redis_cache")
        fallback["cache_bypassed"] = bool(bypass_cache)
        return fallback
    except Exception as exc:
        logger.error("Structured AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = prompt[:500]
        fallback["prompt_full"] = prompt
        fallback["prompt_parts"] = prompt_parts
        fallback["analysis_path"] = "fallback_error"
        fallback["cache_hit"] = False
        fallback["cache_bypassed"] = bool(bypass_cache)
        return fallback


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
    labels = _amount_labels(prompt_config).get(field_name) or ()
    if not labels:
        return None

    candidates: list[float] = []
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
            reject in line_lower
            for reject in ("subtotal", "sub total", "tax exclusive", "sin impuestos")
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
                amount_candidates = _extract_amount_candidates_from_line(lookahead)
                if amount_candidates:
                    break
        for amount in reversed(amount_candidates):
            candidates.append(amount)
            break

    if not candidates:
        return None
    if field_name == "subtotal":
        return max(candidates)
    return candidates[-1]


def _extract_contextual_max_amount(content: str) -> float | None:
    keywords = (
        re.compile(r"\btotal\b"),
        re.compile(r"\bsubtotal\b"),
        re.compile(r"\bsub total\b"),
        re.compile(r"\biva\b"),
        re.compile(r"\bvat\b"),
        re.compile(r"\bigv\b"),
        re.compile(r"\bimpuesto\b"),
    )
    candidates: list[float] = []
    for raw_line in str(content or "").splitlines():
        line = " ".join(raw_line.split()).strip()
        if not line:
            continue
        line_lower = line.lower()
        if not any(pattern.search(line_lower) for pattern in keywords):
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


def _apply_high_evidence_ocr_repairs(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    prompt_config: dict[str, Any] | None = None,
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

    quality = _estimate_text_quality(content, ai_runtime=cfg)
    labeled_total = _extract_labeled_amount(content, "total_amount", prompt_config=prompt_config)
    labeled_subtotal = _extract_labeled_amount(content, "subtotal", prompt_config=prompt_config)
    labeled_tax = _extract_labeled_amount(content, "tax_amount", prompt_config=prompt_config)
    ocr_issue_date = _extract_issue_date_from_ocr(content)

    if quality["score"] < max(0.0, min(1.0, float(cfg.get("ocr_min_quality") or 0.45))) and not any(
        value is not None
        for value in (labeled_total, labeled_subtotal, labeled_tax, ocr_issue_date)
    ):
        return

    text_digits = _digits_only(content)

    if labeled_total is None:
        labeled_total = _extract_contextual_max_amount(content)
    current_total = fields.get("total_amount")
    if labeled_total is not None and (
        current_total in (None, "")
        or not _numeric_evidence(text_digits, current_total)
        or abs(float(current_total) - labeled_total) > 1.0
    ):
        fields["total_amount"] = labeled_total

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
        fields["subtotal"] = labeled_subtotal
    elif (
        labeled_subtotal is None
        and current_subtotal not in (None, "")
        and not _numeric_evidence(text_digits, current_subtotal)
    ):
        fields["subtotal"] = None

    current_tax = fields.get("tax_amount")
    if labeled_tax is not None and (
        current_tax in (None, "") or not _numeric_evidence(text_digits, current_tax)
    ):
        fields["tax_amount"] = labeled_tax
    elif (
        labeled_tax is None
        and current_tax not in (None, "")
        and not _numeric_evidence(text_digits, current_tax)
    ):
        fields["tax_amount"] = None

    issue_date = fields.get("issue_date")
    if ocr_issue_date and (
        issue_date in (None, "") or not _numeric_evidence(text_digits, issue_date)
    ):
        fields["issue_date"] = ocr_issue_date

    current_vendor_tax_id = fields.get("vendor_tax_id")
    ocr_vendor_tax_id = _extract_tax_id_from_ocr(content)
    if ocr_vendor_tax_id and (
        current_vendor_tax_id in (None, "")
        or _digits_only(current_vendor_tax_id) != ocr_vendor_tax_id
        or not _numeric_evidence(text_digits, current_vendor_tax_id)
    ):
        fields["vendor_tax_id"] = ocr_vendor_tax_id
    elif current_vendor_tax_id not in (None, "") and not _numeric_evidence(
        text_digits, current_vendor_tax_id
    ):
        fields["vendor_tax_id"] = None


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


async def _analyze_with_vision(
    image_bytes: bytes,
    filename: str,
    format_hint: str,
    ocr_content: str = "",
    recipe_config: dict | None = None,
    prompt_config: dict[str, Any] | None = None,
    db: Any = None,
) -> dict[str, Any] | None:
    """Try to analyze a document image using a vision-capable model via Ollama.

    Returns None if no vision model is available, letting the caller fall back
    to the text-based OCR path.
    """
    import base64

    import httpx

    ai_runtime = load_ai_runtime_config(db)

    ollama_url = (
        os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434"
    ).rstrip("/")
    vision_model = os.getenv("OLLAMA_VISION_MODEL", "minicpm-v")

    try:
        probe_timeout = max(1.0, float(ai_runtime.get("vision_probe_timeout_seconds") or 5.0))
        async with httpx.AsyncClient(timeout=probe_timeout) as client:
            tags_resp = await client.get(f"{ollama_url}/api/tags")
            if tags_resp.status_code != 200:
                return None
            available = [m["name"].split(":")[0] for m in tags_resp.json().get("models", [])]
            if vision_model.split(":")[0] not in available:
                logger.info("Vision model '%s' not available, falling back to OCR", vision_model)
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

    user_prompt = (
        f"File: {filename} | Format: {format_hint}\n"
        f"{_build_document_time_context(pc, current_year=current_year)}\n\n"
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

    payload = {
        "model": vision_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": user_prompt,
                "images": [img_b64],
            },
        ],
        "stream": False,
        "options": {
            "temperature": float(ai_runtime.get("vision_temperature") or 0.1),
            "num_predict": max(1, int(ai_runtime.get("vision_num_predict") or 600)),
        },
    }

    try:
        timeout_secs = min(
            30.0,
            max(
                1.0,
                float(
                    os.getenv("OLLAMA_VISION_TIMEOUT")
                    or ai_runtime.get("vision_timeout_seconds")
                    or os.getenv("OLLAMA_TIMEOUT", "30")
                ),
            ),
        )
        timeout = httpx.Timeout(timeout_secs, read=timeout_secs)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

        raw_content = (data.get("message") or {}).get("content", "")
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
            parsed["prompt_sent"] = str(prompt_trace["full_prompt"])[:500]
            parsed["prompt_full"] = prompt_trace["full_prompt"]
            parsed["prompt_parts"] = prompt_trace
            logger.info("Vision analysis succeeded with %s for %s", model_used, filename)
            return parsed

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

    return {
        "doc_type": doc_type,
        "confidence": confidence,
        "reasoning": "Structured bypass: parsed CSV/Excel/JSON directly without LLM.",
        "is_table": bool(fields.get("line_items")) or isinstance(structured_data, list),
        "columns": columns,
        "fields": fields,
        "raw_response": "structured_bypass",
        "model_used": "structured-direct",
        "prompt_sent": "",
        "prompt_full": "",
        "prompt_parts": prompt_parts,
        "analysis_path": "structured_direct",
        "cache_hit": False,
        "cache_bypassed": False,
    }


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
    image_bytes: bytes | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
    prompt_config: dict[str, Any] | None = None,
    db: Any = None,
    reprocess_mode: str = "fast",
    bypass_cache: bool = False,
    deep_reprocess_context: dict[str, Any] | None = None,
    deep_focus_fields: list[str] | None = None,
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
        "prompt_sent": str,
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

    if not has_structured_rows and _should_use_vision_fallback(
        content,
        format_hint,
        image_bytes,
        ai_runtime=ai_runtime,
    ):
        vision_result = await _analyze_with_vision(
            image_bytes,
            filename,
            format_hint,
            content,
            recipe_config,
            prompt_config,
            db=db,
        )
        if vision_result:
            return vision_result

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
        f"Content:\n{content[:content_limit]}\n\n"
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
        )

        raw_content = response.content
        model_used = response.model or "unknown"
        response_metadata = getattr(response, "metadata", None) or {}

        if response.is_error:
            logger.warning("AI analysis failed: %s", response.error)
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = full_prompt[:500]
            fallback["prompt_full"] = full_prompt
            fallback["prompt_parts"] = prompt_trace
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("is_table", False)
            parsed.setdefault("columns", [])
            parsed.setdefault("fields", {})
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
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
            )
            _rebuild_line_item_extra_columns_from_ocr(
                parsed,
                content=content,
                format_hint=format_hint,
                ai_runtime=ai_runtime,
            )
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = full_prompt[:500]
            parsed["prompt_full"] = full_prompt
            parsed["prompt_parts"] = prompt_trace
            parsed["analysis_path"] = "ai_text"
            parsed["cache_hit"] = bool(response_metadata.get("source") == "redis_cache")
            parsed["cache_bypassed"] = bool(bypass_cache or deep_active)
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = full_prompt[:500]
        fallback["prompt_full"] = full_prompt
        fallback["prompt_parts"] = prompt_trace
        fallback["analysis_path"] = "fallback"
        fallback["cache_hit"] = bool(response_metadata.get("source") == "redis_cache")
        fallback["cache_bypassed"] = bool(bypass_cache or deep_active)
        return fallback

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = full_prompt[:500]
        fallback["prompt_full"] = full_prompt
        fallback["prompt_parts"] = prompt_trace
        fallback["analysis_path"] = "fallback_error"
        fallback["cache_hit"] = False
        fallback["cache_bypassed"] = bool(bypass_cache or deep_active)
        return fallback


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
