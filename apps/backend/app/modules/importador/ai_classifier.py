"""Universal AI analyzer for any accounting document in any language."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import unicodedata
from typing import Any

from app.services.ai.base import AITask
from app.services.ai.service import AIService

logger = logging.getLogger("importador.ai")

CONFIDENCE_THRESHOLD = 0.85
_OCR_EVIDENCE_FORMATS = {"IMAGE_OCR", "PDF_OCR", "JPG", "JPEG", "PNG", "IMG", "HEIC", "WEBP"}
_SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# Minimal emergency patterns — used ONLY when both AI and DB are unavailable.
# Extend document types via DB migration (imp_config, module='doc_type_patterns'), not here.
_EMERGENCY_PATTERNS: dict[str, list[str]] = {
    "INVOICE": ["invoice", "factura", "rechnung", "fattura", "fatura", "facture"],
    "RECEIPT": ["receipt", "recibo", "reçu", "quittung", "boleta", "ticket"],
    "BANK_STATEMENT": [
        "bank statement",
        "extracto",
        "kontoauszug",
        "état de compte",
        "estado de cuenta",
    ],
    "PAYROLL": ["payroll", "nomina", "planilla", "lohnabrechnung"],
    "INVENTORY": ["inventory", "inventario", "stock", "bestandsliste"],
    "COSTING": ["costing", "costeo", "kalkulation", "receta"],
}


def _ocr_quality_threshold() -> float:
    raw = (os.getenv("IMPORTADOR_OCR_MIN_QUALITY") or "").strip()
    if not raw:
        return 0.45
    try:
        return max(0.0, min(1.0, float(raw)))
    except ValueError:
        return 0.45


def _estimate_text_quality(text: str) -> dict[str, float]:
    """Estimate whether OCR text is good enough to avoid a vision pass."""
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
    length_score = min(chars / 1200.0, 1.0)
    word_score = min(word_count / 180.0, 1.0)
    alpha_score = min(alpha_ratio / 0.6, 1.0)
    noise_penalty = min(weird_ratio / 0.2, 1.0)

    score = (
        (length_score * 0.35)
        + (word_score * 0.35)
        + (alpha_score * 0.2)
        + ((1 - noise_penalty) * 0.1)
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
) -> bool:
    """Use vision only when OCR text is too weak and we have an image payload."""
    if not image_bytes:
        return False

    normalized_format = str(format_hint or "").strip().upper()
    if normalized_format not in {"IMAGE_OCR", "PDF_OCR", "JPG", "PNG", "IMG", "PDF"}:
        return False

    quality = _estimate_text_quality(content)
    score = quality["score"]
    min_quality = _ocr_quality_threshold()
    needs_vision = score < min_quality or quality["words"] < 18

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


def _value_token_evidence(text_normalized: str, value: Any, *, min_len: int = 4) -> bool:
    sample = _normalize_evidence_text(str(value or ""))
    if not sample:
        return False
    stop_tokens = {
        "cliente",
        "customer",
        "proveedor",
        "vendor",
        "empresa",
        "company",
        "concepto",
        "concept",
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


def _currency_evidence(text_normalized: str, value: Any) -> bool:
    raw = str(value or "").strip().upper()
    if not raw:
        return False
    currency_markers = {
        "USD": ["usd", "us$", "$", "dolar", "dolares"],
        "EUR": ["eur", "euro", "euros", "€"],
        "PEN": ["pen", "s/", "sol", "soles"],
        "$": ["$", "usd", "dolar", "dolares"],
        "S/": ["s/", "pen", "sol", "soles"],
    }
    markers = currency_markers.get(raw, [raw.lower()])
    return any(marker in text_normalized for marker in markers)


def _line_items_evidence(text_normalized: str, text_digits: str, value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for item in value:
        if not isinstance(item, dict):
            continue
        description = item.get("description")
        if description and _value_token_evidence(text_normalized, description):
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
) -> int:
    normalized_format = str(format_hint or "").strip().upper()
    if normalized_format not in {"IMAGE_OCR", "PDF_OCR", "JPG", "PNG", "IMG"}:
        return 0

    quality = _estimate_text_quality(content)
    if quality["score"] >= _ocr_quality_threshold() and quality["words"] >= 18:
        return 0

    text_normalized = _normalize_evidence_text(content)
    text_digits = _digits_only(content)
    cleared = 0

    evidence_checks: dict[str, Any] = {
        "vendor": lambda value: _value_token_evidence(text_normalized, value),
        "vendor_tax_id": lambda value: _numeric_evidence(text_digits, value),
        "customer": lambda value: _value_token_evidence(text_normalized, value),
        "customer_tax_id": lambda value: _numeric_evidence(text_digits, value),
        "doc_number": lambda value: (
            _value_token_evidence(text_normalized, value, min_len=3)
            or _numeric_evidence(text_digits, value, min_len=5)
        ),
        "issue_date": lambda value: _numeric_evidence(text_digits, value),
        "currency": lambda value: _currency_evidence(text_normalized, value),
        "payment_method": lambda value: _value_token_evidence(text_normalized, value),
        "payment_terms": lambda value: _value_token_evidence(text_normalized, value),
        "concept": lambda value: _value_token_evidence(text_normalized, value),
        "subtotal": lambda value: _numeric_evidence(text_digits, value),
        "tax_amount": lambda value: _numeric_evidence(text_digits, value),
        "total_amount": lambda value: _numeric_evidence(text_digits, value),
        "line_items": lambda value: _line_items_evidence(text_normalized, text_digits, value),
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
) -> None:
    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return

    cleared = _blank_low_evidence_fields(fields, content=content, format_hint=format_hint)
    if cleared <= 0:
        return

    try:
        parsed["confidence"] = min(float(parsed.get("confidence") or 0.0), 0.45)
    except (TypeError, ValueError):
        parsed["confidence"] = 0.45

    reason = str(parsed.get("reasoning") or "").strip()
    guard_reason = (
        f"Low OCR evidence: cleared {cleared} unsupported field(s) to avoid hallucinated data."
    )
    parsed["reasoning"] = f"{reason} {guard_reason}".strip() if reason else guard_reason


def _build_structured_classification_prompt(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None,
    prompt_config: dict[str, Any] | None = None,
) -> str:
    rc = recipe_config or {}
    pc = prompt_config or {}
    system_prefix = str(rc.get("prompt_system") or "").strip()
    doc_type_instruction = str(
        pc.get("doc_type_instruction")
        or "Use concise uppercase labels such as INVOICE, RECEIPT, CREDIT_NOTE, "
        "BANK_STATEMENT, BANK_MOVEMENTS, INVENTORY, PRICE_LIST, COSTING, PAYROLL, OTHER."
    ).strip()
    current_year = datetime.datetime.now().year

    prompt = (
        "Classify this structured accounting dataset.\n"
        "The content contains column headers and a few sample rows, not the full file.\n"
        "Return ONLY valid JSON with keys: doc_type, confidence, reasoning.\n"
        f"File: {filename} | Format: {format_hint}\n"
        f"Current year: {current_year}\n\n"
        f"Structured preview:\n{content[:2500]}\n\n"
        f"{doc_type_instruction}"
    )

    if system_prefix:
        prompt = system_prefix + "\n\n" + prompt
    return prompt


def _build_dynamic_fields_prompt(
    canonical_fields: dict[str, dict] | None,
    field_descriptions: dict[str, str] | None = None,
) -> str:
    descriptions = field_descriptions or {}
    if not canonical_fields:
        return (
            '    "vendor": "issuing/selling party name or null",\n'
            '    "vendor_tax_id": "tax ID of the issuer or null",\n'
            '    "customer": "receiving/buying party name or null",\n'
            '    "customer_tax_id": "tax ID of the buyer or null",\n'
            '    "doc_number": "document reference number or null",\n'
            '    "issue_date": "YYYY-MM-DD or null",\n'
            '    "total_amount": NUMBER or null,\n'
            '    "subtotal": NUMBER or null,\n'
            '    "tax_amount": NUMBER or null,\n'
            '    "currency": "ISO 4217 code or null",\n'
            '    "payment_method": "payment method exactly as printed or null",\n'
            '    "payment_terms": "payment terms exactly as printed or null",\n'
            '    "line_items": [{"description":"...","quantity":number,"unit_price":number,"total_price":number,"extra_columns":{"ColNameAsInDoc":"value"}}] or []'
        )

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
    pc = prompt_config or {}
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
    configured_rules.append(
        f"YEAR sanity check: we are in {current_year}. If you read '16' as year, it is almost certainly '26' (20{current_year % 100})."
    )
    configured_rules.append(
        "line_items: only list actual PRODUCTS. "
        "For every visible line-item column that does not clearly map to the configured base fields, "
        "preserve it verbatim in extra_columns using the original header label and cell value. "
        "Do not drop visible line-item columns just because their meaning is uncertain."
    )
    return configured_rules


async def _analyze_structured_document(
    content: str,
    filename: str,
    format_hint: str,
    recipe_config: dict | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    prompt_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cheap classification path for already structured datasets."""
    prompt = _build_structured_classification_prompt(
        content,
        filename,
        format_hint,
        recipe_config,
        prompt_config=prompt_config,
    )

    try:
        response = await AIService.query(
            task=AITask.CLASSIFICATION,
            prompt=prompt,
            temperature=0.1,
            max_tokens=220,
            module="importador",
            enable_recovery=True,
        )
        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": True, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = prompt[:500]
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
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = prompt[:500]
        return fallback
    except Exception as exc:
        logger.error("Structured AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": True, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = prompt[:500]
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
    for raw_line in str(content or "").splitlines():
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
        for amount in reversed(_extract_amount_candidates_from_line(segment)):
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

    normalized = _normalize_evidence_text(text)
    written_match = re.search(
        r"\b(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(20\d{2})\b",
        normalized,
    )
    if not written_match:
        return None
    month = _SPANISH_MONTHS.get(written_match.group(2))
    if month is None:
        return None
    day = int(written_match.group(1))
    year = int(written_match.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def _apply_high_evidence_ocr_repairs(
    parsed: dict[str, Any],
    *,
    content: str,
    format_hint: str,
    prompt_config: dict[str, Any] | None = None,
) -> None:
    normalized_format = str(format_hint or "").strip().upper()
    if normalized_format not in _OCR_EVIDENCE_FORMATS:
        return

    fields = parsed.get("fields")
    if not isinstance(fields, dict):
        return

    quality = _estimate_text_quality(content)
    labeled_total = _extract_labeled_amount(
        content, "total_amount", prompt_config=prompt_config
    )
    labeled_subtotal = _extract_labeled_amount(content, "subtotal", prompt_config=prompt_config)
    labeled_tax = _extract_labeled_amount(content, "tax_amount", prompt_config=prompt_config)
    ocr_issue_date = _extract_issue_date_from_ocr(content)

    if quality["score"] < _ocr_quality_threshold() and not any(
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
) -> None:
    normalized_format = str(format_hint or "").strip().upper()
    if normalized_format not in _OCR_EVIDENCE_FORMATS:
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


def _build_additional_field_hints(recipe_config: dict | None) -> str:
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
    return "Learned hints from previously confirmed similar documents:\n" + "\n".join(lines)


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
) -> dict[str, Any] | None:
    """Try to analyze a document image using a vision-capable model via Ollama.

    Returns None if no vision model is available, letting the caller fall back
    to the text-based OCR path.
    """
    import base64
    import os

    import httpx

    ollama_url = (
        os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434"
    ).rstrip("/")
    vision_model = os.getenv("OLLAMA_VISION_MODEL", "minicpm-v")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
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
    pc = prompt_config or {}
    system_prompt = (
        rc.get("prompt_system")
        or pc.get("extraction_system")
        or (
            "You are a universal accounting document analyzer with vision capabilities. "
            "You can read documents in ANY language. Extract all visible information accurately."
        )
    )

    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or "taxable base before tax. Number or null"
    _f_tax = _fd.get("tax_amount") or "total tax (VAT/IVA/IGV/GST). Number or null if absent"
    learned_hints = _build_additional_field_hints(recipe_config)
    dynamic_fields_prompt = _build_dynamic_fields_prompt(
        None,
        {
            **_fd,
            "subtotal": _f_subtotal,
            "tax_amount": _f_tax,
        },
    )

    current_year = datetime.datetime.now().year
    vision_preamble = str(
        pc.get("vision_extraction_preamble")
        or "Read this document image very carefully, character by character."
    ).strip()
    doc_type_instruction = str(
        pc.get("doc_type_instruction")
        or "INVOICE, RECEIPT, TICKET, CREDIT_NOTE, PURCHASE_ORDER, QUOTE, "
        "DELIVERY_NOTE, INVENTORY, PRICE_LIST, COSTING, PAYROLL, BANK_STATEMENT, "
        "BANK_MOVEMENTS, or any descriptive label"
    ).strip()
    critical_rules_text = "\n".join(
        f"- {rule}"
        for rule in _build_configured_rules(
            prompt_config=pc,
            current_year=current_year,
            vision_mode=True,
        )
    )
    response_contract = _build_json_response_contract(
        dynamic_fields_prompt=dynamic_fields_prompt,
        doc_type_instruction=doc_type_instruction,
        is_table_literal="false",
        columns_literal="[]",
        reasoning_hint="brief explanation",
    )

    user_prompt = (
        f"File: {filename} | Format: {format_hint}\n"
        f"CONTEXT: Current year is {current_year}. Most documents are from {current_year - 1}-{current_year}.\n\n"
        f"{vision_preamble}\n"
        "Respond ONLY with valid JSON:\n"
        f"{response_contract}\n"
        "CRITICAL RULES:\n"
        f"{critical_rules_text}"
    )

    custom_user = rc.get("prompt_user")
    if custom_user:
        user_prompt += f"\n\nAdditional instructions:\n{custom_user}"
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    img_b64 = base64.b64encode(_resize_image_for_vision(image_bytes)).decode("utf-8")

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
        "options": {"temperature": 0.1, "num_predict": 600},
    }

    try:
        timeout_secs = float(
            os.getenv("OLLAMA_VISION_TIMEOUT") or os.getenv("OLLAMA_TIMEOUT", "45")
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
            parsed.setdefault("reasoning", "Vision model analysis")
            _clean_vision_fields(parsed.get("fields") or {})
            _apply_low_evidence_guard(parsed, content=ocr_content, format_hint=format_hint)
            _rebuild_line_item_extra_columns_from_ocr(
                parsed,
                content=ocr_content,
                format_hint=format_hint,
            )
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = (system_prompt + "\n\n" + user_prompt)[:500]
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


async def analyze_document(
    content: str,
    filename: str = "",
    format_hint: str = "",
    has_structured_rows: bool = False,
    recipe_config: dict | None = None,
    image_bytes: bytes | None = None,
    fallback_patterns: dict[str, list[str]] | None = None,
    canonical_fields: dict[str, dict] | None = None,
    prompt_config: dict[str, Any] | None = None,
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
    if has_structured_rows:
        return await _analyze_structured_document(
            content,
            filename,
            format_hint,
            recipe_config,
            fallback_patterns=fallback_patterns,
            prompt_config=prompt_config,
        )

    if not has_structured_rows and _should_use_vision_fallback(content, format_hint, image_bytes):
        vision_result = await _analyze_with_vision(
            image_bytes, filename, format_hint, content, recipe_config, prompt_config
        )
        if vision_result:
            return vision_result

    rc = recipe_config or {}
    pc = prompt_config or {}

    system_prompt = (
        rc.get("prompt_system")
        or pc.get("extraction_system")
        or (
            "You are a universal accounting document analyzer. "
            "Always respond with valid JSON using the configured canonical fields."
        )
    )

    # Field descriptions can be customized per tenant via recipe_config["field_descriptions"].
    # Defaults are intentionally generic — locale-specific hints belong in the DB config.
    _fd = rc.get("field_descriptions") or {}
    _f_subtotal = _fd.get("subtotal") or (
        "taxable base amount before tax (subtotal, net, base imponible, or similar). Number or null"
    )
    _f_tax = _fd.get("tax_amount") or (
        "total tax amount (VAT/IVA/IGV/GST/TVA or equivalent). Use 0 if present but zero. Number or null if absent"
    )
    learned_hints = _build_additional_field_hints(recipe_config)
    dynamic_fields_prompt = _build_dynamic_fields_prompt(
        canonical_fields,
        {
            **_fd,
            "subtotal": _f_subtotal,
            "tax_amount": _f_tax,
        },
    )

    tabular_note = (
        f"{pc.get('structured_table_note') or 'Structured table input.'}\n\n"
        if has_structured_rows
        else ""
    )

    content_limit = 4000 if has_structured_rows else 7000

    current_year = datetime.datetime.now().year
    doc_type_instruction = str(
        pc.get("doc_type_instruction")
        or "A short uppercase label describing the document type in English. "
        "Use standard business labels when they clearly apply. Use OTHER only if truly unclassifiable."
    ).strip()
    critical_rules_text = "\n".join(
        f"- {rule}"
        for rule in _build_configured_rules(
            prompt_config=pc,
            current_year=current_year,
            vision_mode=False,
        )
    )
    response_contract = _build_json_response_contract(
        dynamic_fields_prompt=dynamic_fields_prompt,
        doc_type_instruction=doc_type_instruction,
        is_table_literal="true or false",
        columns_literal='["col1", "col2"]',
        reasoning_hint="brief explanation of classification",
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
        f"CONTEXT: Current year is {current_year}. Most documents are from {current_year - 1}-{current_year}.\n"
        f"{_hint_line}\n"
        f"Content:\n{content[:content_limit]}\n\n"
        "Analyze the document and respond ONLY with valid JSON:\n"
        f"{response_contract}\n"
        "CRITICAL rules:\n"
        f"{critical_rules_text}"
    )

    custom_user_prompt = rc.get("prompt_user")
    if custom_user_prompt:
        user_prompt += f"\n\nAdditional extraction instructions:\n{custom_user_prompt}"
    if learned_hints:
        user_prompt += f"\n\n{learned_hints}"

    full_prompt = system_prompt.rstrip() + "\n\n" + user_prompt

    try:
        response = await AIService.query(
            task=AITask.EXTRACTION,
            prompt=full_prompt,
            temperature=0.1,
            max_tokens=1500,
            module="importador",
            enable_recovery=True,
        )

        raw_content = response.content
        model_used = response.model or "unknown"

        if response.is_error:
            logger.warning("AI analysis failed: %s", response.error)
            fallback = _fallback_classify(content, filename, fallback_patterns)
            fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
            fallback["raw_response"] = response.error
            fallback["model_used"] = model_used
            fallback["prompt_sent"] = full_prompt[:500]
            return fallback

        parsed = _parse_json_response(raw_content)
        if parsed and parsed.get("doc_type"):
            parsed.setdefault("is_table", False)
            parsed.setdefault("columns", [])
            parsed.setdefault("fields", {})
            parsed.setdefault("confidence", 0.7)
            parsed.setdefault("reasoning", "")
            _apply_low_evidence_guard(parsed, content=content, format_hint=format_hint)
            _apply_high_evidence_ocr_repairs(
                parsed,
                content=content,
                format_hint=format_hint,
                prompt_config=pc,
            )
            _rebuild_line_item_extra_columns_from_ocr(
                parsed,
                content=content,
                format_hint=format_hint,
            )
            parsed["raw_response"] = raw_content
            parsed["model_used"] = model_used
            parsed["prompt_sent"] = full_prompt[:500]
            return parsed

        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = raw_content
        fallback["model_used"] = model_used
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback

    except Exception as exc:
        logger.error("AI analysis error: %s", exc)
        fallback = _fallback_classify(content, filename, fallback_patterns)
        fallback.update({"is_table": has_structured_rows, "columns": [], "fields": {}})
        fallback["raw_response"] = str(exc)
        fallback["model_used"] = "fallback"
        fallback["prompt_sent"] = full_prompt[:500]
        return fallback


def _fallback_classify(
    text: str,
    filename: str,
    extra_patterns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Rule-based classification used only when the AI service is unavailable.

    Uses _EMERGENCY_PATTERNS (universal cross-language terms) plus any
    tenant-specific patterns passed via extra_patterns.
    """
    text_lower = text.lower()
    fn_lower = filename.lower()

    patterns = {**_EMERGENCY_PATTERNS, **(extra_patterns or {})}

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
