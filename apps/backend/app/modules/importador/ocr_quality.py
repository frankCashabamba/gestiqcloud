"""Heuristics to estimate OCR text quality."""

from __future__ import annotations

import datetime
import re
from typing import Any

from .runtime_config import load_ocr_runtime_config

_USEFUL_MARKERS = (
    "factura",
    "invoice",
    "receipt",
    "ticket",
    "boleta",
    "subtotal",
    "total",
    "tax",
    "iva",
    "igv",
    "vat",
    "fecha",
    "date",
    "ruc",
    "nit",
    "cif",
    "currency",
    "moneda",
    "vendor",
    "proveedor",
    "customer",
    "cliente",
    "description",
    "descripcion",
    "concepto",
    "item",
    "qty",
    "quantity",
    "price",
    "amount",
)


def _count_useful_markers(normalized: str) -> int:
    lowered = normalized.lower()
    return sum(1 for marker in _USEFUL_MARKERS if marker in lowered)


def estimate_text_quality(
    text: str,
    *,
    ocr_runtime: dict[str, Any] | None = None,
    ai_runtime: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Estimate OCR quality using local heuristics and runtime config."""
    cfg = ocr_runtime or ai_runtime or load_ocr_runtime_config(None)
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return {"score": 0.0, "chars": 0.0, "words": 0.0}

    chars = len(normalized)
    tokens = re.findall(r"[^\W_]{2,}", normalized, flags=re.UNICODE)
    word_count = len(tokens)
    unique_tokens = {token.lower() for token in tokens}
    repeated_tokens = max(0, len(tokens) - len(unique_tokens))
    repeat_ratio = repeated_tokens / max(len(tokens), 1)
    line_count = sum(1 for line in str(text or "").splitlines() if line.strip())
    useful_hits = _count_useful_markers(normalized)

    alpha_chars = sum(1 for ch in normalized if ch.isalpha())
    digit_chars = sum(1 for ch in normalized if ch.isdigit())
    alnum_chars = sum(1 for ch in normalized if ch.isalnum())
    weird_chars = sum(
        1
        for ch in normalized
        if not (ch.isalpha() or ch.isdigit() or ch.isspace() or ch in ".,;:/-_#%()[]{}+*'\"@$|")
    )

    alpha_ratio = alpha_chars / max(alnum_chars, 1)
    digit_ratio = digit_chars / max(chars, 1)
    weird_ratio = weird_chars / max(chars, 1)

    length_score = min(chars / max(float(cfg.get("ocr_length_target_chars") or 1200.0), 1.0), 1.0)
    word_score = min(word_count / max(float(cfg.get("ocr_word_target") or 180.0), 1.0), 1.0)
    alpha_score = min(
        alpha_ratio / max(float(cfg.get("ocr_alpha_ratio_target") or 0.6), 0.01),
        1.0,
    )
    clean_score = 1.0 - min(
        weird_ratio / max(float(cfg.get("ocr_noise_ratio_limit") or 0.2), 0.01),
        1.0,
    )
    useful_score = min(
        useful_hits / max(float(cfg.get("ocr_useful_marker_target") or 4.0), 1.0),
        1.0,
    )

    repeat_limit = max(float(cfg.get("ocr_repeat_ratio_limit") or 0.35), 0.01)
    repetition_penalty = min(repeat_ratio / repeat_limit, 1.0)
    short_penalty = 0.0
    if chars < int(cfg.get("weak_text_min_chars") or 24):
        short_penalty += 0.22
    if word_count < int(cfg.get("weak_text_min_words") or 4):
        short_penalty += 0.18

    # Use explicit None-check for useful weight so that an explicit 0.0 in the config
    # (e.g. ai_runtime where the 4 primary weights already sum to 1.0) is respected
    # instead of being treated as falsy by the `or` operator.
    _useful_weight_raw = cfg.get("ocr_score_weight_useful")
    _useful_weight = float(_useful_weight_raw) if _useful_weight_raw is not None else 0.15
    base_score = (
        (length_score * float(cfg.get("ocr_score_weight_length") or 0.30))
        + (word_score * float(cfg.get("ocr_score_weight_words") or 0.25))
        + (alpha_score * float(cfg.get("ocr_score_weight_alpha") or 0.15))
        + (clean_score * float(cfg.get("ocr_score_weight_clean") or 0.15))
        + (useful_score * _useful_weight)
    )
    score = base_score
    score *= max(0.45, 1.0 - (repetition_penalty * 0.35))
    score -= short_penalty
    if useful_hits >= 2:
        score += 0.05
    if line_count >= 3 and useful_hits >= 1:
        score += 0.03

    score = max(0.0, min(1.0, score))
    result: dict[str, float] = {
        "score": round(score, 3),
        "chars": float(chars),
        "words": float(word_count),
        "alpha_ratio": round(alpha_ratio, 3),
        "weird_ratio": round(weird_ratio, 3),
        "repeat_ratio": round(repeat_ratio, 3),
        "digit_ratio": round(digit_ratio, 3),
        "unique_word_ratio": round(len(unique_tokens) / max(len(tokens), 1), 3),
        "line_count": float(line_count),
        "useful_hits": float(useful_hits),
    }
    return result


# ---------------------------------------------------------------------------
# Combined score (text + structured fields) and plausibility checks.
# ---------------------------------------------------------------------------

# Tax-id valid lengths across the markets we support today.
# - Ecuador RUC: 13, CI: 10
# - Peru RUC: 11
# - Spain CIF/NIF: 9 (kept as text, length only — letter validation is out of scope)
# - Colombia NIT: 9-10
_VALID_TAX_ID_LENGTHS = {9, 10, 11, 13}

# Anything above this for a single document is almost certainly a misread total.
_MAX_PLAUSIBLE_TOTAL = 10_000_000.0

# Year window for issue dates: docs older than this are usually OCR junk.
_MIN_PLAUSIBLE_YEAR = 2000

_KEYWORD_HINTS = ("ruc", "nit", "cif", "rfc", "total", "subtotal", "fecha", "factura")


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace("\u00a0", "").replace(" ", "")
    # Heurística simple: si tiene coma y punto se asume miles + decimal coma o
    # punto. Si solo tiene coma -> coma decimal. Si solo punto -> punto decimal.
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _coerce_date(value: Any) -> datetime.date | None:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    raw = str(value).strip()
    if not raw:
        return None
    # Common formats; intentionally narrow to avoid false positives.
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%Y%m%d"):
        try:
            return datetime.datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _looks_like_tax_id(value: Any) -> bool:
    raw = re.sub(r"\D", "", str(value or ""))
    return len(raw) in _VALID_TAX_ID_LENGTHS


def _looks_like_positive_number(value: Any) -> bool:
    num = _coerce_float(value)
    return num is not None and num > 0


def _looks_like_plausible_date(value: Any) -> bool:
    parsed = _coerce_date(value)
    if parsed is None:
        return False
    today = datetime.date.today()
    return _MIN_PLAUSIBLE_YEAR <= parsed.year <= today.year + 1


def _line_items_consistent(line_items: Any) -> bool:
    """True if at least one line item has qty * unit_price ≈ total_price (±5%)."""
    if not isinstance(line_items, list) or not line_items:
        return False
    for row in line_items:
        if not isinstance(row, dict):
            continue
        qty = _coerce_float(row.get("quantity"))
        unit = _coerce_float(row.get("unit_price"))
        total = _coerce_float(row.get("total_price"))
        if qty is None or unit is None or total is None:
            continue
        expected = qty * unit
        if abs(expected) < 0.01:
            continue
        if abs(total - expected) / abs(expected) <= 0.05:
            return True
    return False


def has_plausibility_issues(fields: dict[str, Any] | None) -> list[str]:
    """Return a list of plausibility issue codes for the extracted fields.

    Empty list ⇒ no issues detected. Each code is a short, log-friendly string
    so it can be appended to ``ImportPipelineDecision.reasons`` without further
    formatting.

    Detected issues:
        * ``total_non_positive``      - total_amount ≤ 0
        * ``total_unrealistic``       - total_amount > 10M (likely OCR misread)
        * ``date_too_far_future``     - issue_date.year > today.year + 1
        * ``date_too_far_past``       - issue_date.year < 2000
        * ``vendor_tax_id_invalid``   - vendor_tax_id length not in {9,10,11,13}
        * ``customer_tax_id_invalid`` - customer_tax_id length not in {9,10,11,13}
        * ``line_items_arithmetic_mismatch`` - any row where qty*price ≠ total (>5%)
    """
    fields = fields or {}
    issues: list[str] = []

    total = _coerce_float(fields.get("total_amount"))
    if total is not None:
        if total <= 0:
            issues.append("total_non_positive")
        elif total > _MAX_PLAUSIBLE_TOTAL:
            issues.append("total_unrealistic")

    issue_date = _coerce_date(fields.get("issue_date"))
    if issue_date is not None:
        today = datetime.date.today()
        if issue_date.year > today.year + 1:
            issues.append("date_too_far_future")
        elif issue_date.year < _MIN_PLAUSIBLE_YEAR:
            issues.append("date_too_far_past")

    vendor_tax_id = str(fields.get("vendor_tax_id") or "").strip()
    if vendor_tax_id and not _looks_like_tax_id(vendor_tax_id):
        issues.append("vendor_tax_id_invalid")

    customer_tax_id = str(fields.get("customer_tax_id") or "").strip()
    if customer_tax_id and not _looks_like_tax_id(customer_tax_id):
        issues.append("customer_tax_id_invalid")

    line_items = fields.get("line_items")
    if isinstance(line_items, list) and line_items:
        bad = 0
        for row in line_items:
            if not isinstance(row, dict):
                continue
            qty = _coerce_float(row.get("quantity"))
            unit = _coerce_float(row.get("unit_price"))
            tot = _coerce_float(row.get("total_price"))
            if qty is None or unit is None or tot is None:
                continue
            expected = qty * unit
            if abs(expected) < 0.01:
                continue
            ratio = abs(tot - expected) / abs(expected)
            if ratio > 0.05:
                bad += 1
        if bad >= 1:
            issues.append("line_items_arithmetic_mismatch")

    return issues


def ocr_quality_score(
    text: str,
    fields: dict[str, Any] | None = None,
    *,
    ocr_runtime: dict[str, Any] | None = None,
) -> float:
    """Combined OCR quality score in [0.0, 1.0].

    Three weighted components:
        * 0.50 ``estimate_text_quality`` (length, alpha ratio, useful markers)
        * 0.20 raw-text keyword presence (RUC, TOTAL, FECHA, …)
        * 0.30 structured-field signal (presence + plausibility)

    Then a small penalty (capped at -0.25) for each detected plausibility issue.

    A value < 0.7 is the trigger used by the router to escalate to vision_fallback.
    """
    base = float(estimate_text_quality(text, ocr_runtime=ocr_runtime).get("score") or 0.0)
    fields = fields or {}

    lowered = (text or "").lower()
    keyword_hits = sum(1 for kw in _KEYWORD_HINTS if kw in lowered)
    keyword_score = min(keyword_hits / 4.0, 1.0)

    field_signals = (
        _looks_like_positive_number(fields.get("total_amount")),
        _looks_like_plausible_date(fields.get("issue_date")),
        _looks_like_tax_id(fields.get("vendor_tax_id")),
        bool(str(fields.get("vendor") or "").strip()),
        bool(str(fields.get("doc_number") or "").strip()),
        _line_items_consistent(fields.get("line_items")),
    )
    field_score = sum(1 for ok in field_signals if ok) / float(len(field_signals))

    issues = has_plausibility_issues(fields)
    penalty = min(0.25, 0.08 * len(issues))

    score = (0.50 * base) + (0.20 * keyword_score) + (0.30 * field_score) - penalty
    return round(max(0.0, min(1.0, score)), 3)
